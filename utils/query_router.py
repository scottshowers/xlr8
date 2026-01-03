"""
Intelligent Query Router - Self-Healing & Learning
===================================================

Philosophy: Try everything, score results, pick best, learn.

NO regex pattern matching. Instead:
1. Check if structured data exists → TRY SQL first
2. Use fuzzy matching for entity detection
3. Learn from user corrections
4. Never return "not found" without trying alternatives

Author: XLR8 Team
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class QueryType(Enum):
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    HYBRID = "hybrid"
    GENERAL = "general"


# Common HR/Payroll entities - used for fuzzy matching
HR_ENTITIES = {
    'employee': ['employee', 'emp', 'ee', 'worker', 'staff', 'personnel', 'associate'],
    'earnings': ['earnings', 'earning', 'earn', 'pay', 'wages', 'compensation', 'income'],
    'deductions': ['deductions', 'deduction', 'ded', 'withholding', 'benefit'],
    'department': ['department', 'dept', 'division', 'unit', 'group', 'team', 'org'],
    'job': ['job', 'position', 'role', 'title', 'occupation'],
    'location': ['location', 'loc', 'site', 'branch', 'office', 'workplace'],
    'pay_group': ['pay group', 'paygroup', 'pay_group', 'payroll group', 'pay cycle'],
    'tax': ['tax', 'taxes', 'withholding', 'fit', 'sit', 'lit', 'fica'],
    'bank': ['bank', 'direct deposit', 'dd', 'ach', 'routing'],
    'benefit': ['benefit', 'benefits', 'insurance', 'health', '401k', 'retirement'],
    'hours': ['hours', 'hrs', 'time', 'attendance', 'worked'],
    'rate': ['rate', 'hourly', 'salary', 'annual', 'wage rate'],
}

# Action words that indicate data retrieval (not explanation)
DATA_ACTIONS = [
    'list', 'show', 'get', 'find', 'display', 'give', 'tell', 'what are',
    'how many', 'count', 'total', 'sum', 'average', 'all', 'every',
    'which', 'who', 'where', 'export', 'download', 'report'
]


class IntelligentQueryRouter:
    """
    Self-healing query router that:
    1. Checks for structured data first
    2. Uses fuzzy matching instead of regex
    3. Learns from corrections
    """
    
    def __init__(self, learning_db_path: str = "/data/query_learning.json"):
        self.learning_db_path = learning_db_path
        self.learned_patterns = self._load_learned_patterns()
    
    def _load_learned_patterns(self) -> Dict:
        """Load learned query patterns from storage"""
        import json
        import os
        
        if os.path.exists(self.learning_db_path):
            try:
                with open(self.learning_db_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'queries': {}, 'entities': {}}
    
    def _save_learned_patterns(self):
        """Persist learned patterns"""
        import json
        import os
        
        os.makedirs(os.path.dirname(self.learning_db_path), exist_ok=True)
        with open(self.learning_db_path, 'w') as f:
            json.dump(self.learned_patterns, f, indent=2)
    
    def fuzzy_match(self, text: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
        """Fuzzy match text against candidates"""
        text_lower = text.lower()
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            # Direct substring match
            if candidate.lower() in text_lower or text_lower in candidate.lower():
                return candidate
            
            # Fuzzy match
            score = SequenceMatcher(None, text_lower, candidate.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        
        return best_match
    
    def extract_entities(self, query: str) -> List[Dict]:
        """Extract HR/Payroll entities from query using fuzzy matching"""
        query_lower = query.lower()
        found_entities = []
        
        for entity_type, variations in HR_ENTITIES.items():
            for variation in variations:
                if variation in query_lower:
                    found_entities.append({
                        'type': entity_type,
                        'match': variation,
                        'confidence': 1.0
                    })
                    break
            else:
                # Try fuzzy match on query words
                words = query_lower.split()
                for word in words:
                    if len(word) > 2:
                        match = self.fuzzy_match(word, variations, threshold=0.7)
                        if match:
                            found_entities.append({
                                'type': entity_type,
                                'match': match,
                                'confidence': 0.8
                            })
                            break
        
        return found_entities
    
    def is_data_query(self, query: str) -> Tuple[bool, float]:
        """
        Determine if query is asking for data (vs explanation).
        Returns (is_data_query, confidence)
        """
        query_lower = query.lower()
        
        # Check for data action words
        action_matches = sum(1 for action in DATA_ACTIONS if action in query_lower)
        
        # Check for question patterns that want data
        data_questions = [
            r'\bhow many\b', r'\bhow much\b',
            r'\bwhat (are|is) the\b', r'\bwhat .+ (are|is) there\b',
            r'\blist\b', r'\bshow\b', r'\bgive me\b',
            r'\bwhich\b', r'\bwho\b',
        ]
        question_matches = sum(1 for p in data_questions if re.search(p, query_lower))
        
        # Check for explanation patterns (reduce confidence)
        explanation_patterns = [
            r'\bwhat does .+ mean\b', r'\bexplain\b', r'\bwhy\b',
            r'\bhow (do|does|should|can|to)\b', r'\bdefine\b',
        ]
        explanation_matches = sum(1 for p in explanation_patterns if re.search(p, query_lower))
        
        # Calculate confidence
        data_score = action_matches * 0.3 + question_matches * 0.4
        explanation_score = explanation_matches * 0.5
        
        confidence = min(1.0, max(0.0, data_score - explanation_score + 0.5))
        is_data = confidence > 0.5
        
        return is_data, confidence
    
    def route_query(
        self,
        query: str,
        has_structured_data: bool = False,
        has_rag_data: bool = False,
        structured_tables: List[str] = None
    ) -> Dict[str, Any]:
        """
        Intelligently route query to best data source.
        
        PHILOSOPHY: If structured data exists and query looks like data request,
        TRY SQL FIRST. Only fall back to RAG if SQL fails.
        """
        structured_tables = structured_tables or []
        
        # Extract entities from query
        entities = self.extract_entities(query)
        entity_types = [e['type'] for e in entities]
        
        # Check if this is a data query
        is_data, data_confidence = self.is_data_query(query)
        
        # Check for table name matches
        table_matches = []
        query_lower = query.lower()
        for table in structured_tables:
            # Extract readable name from table (e.g., "project__file__earnings" -> "earnings")
            table_parts = table.split('__')
            readable_name = table_parts[-1] if table_parts else table
            
            if readable_name.lower() in query_lower:
                table_matches.append(table)
            else:
                # Fuzzy match
                for word in query_lower.split():
                    if len(word) > 3 and SequenceMatcher(None, word, readable_name.lower()).ratio() > 0.7:
                        table_matches.append(table)
                        break
        
        # Decision logic
        result = {
            'query': query,
            'entities': entities,
            'is_data_query': is_data,
            'data_confidence': data_confidence,
            'table_matches': table_matches,
            'reasoning': []
        }
        
        # RULE 1: If we have structured data and this looks like a data query, USE IT
        if has_structured_data and is_data:
            result['route'] = QueryType.STRUCTURED
            result['reasoning'].append(f"Data query detected (confidence: {data_confidence:.0%})")
            result['reasoning'].append(f"Structured data available")
            if table_matches:
                result['reasoning'].append(f"Table matches: {table_matches}")
            if entities:
                result['reasoning'].append(f"Entities found: {entity_types}")
            result['fallback'] = QueryType.UNSTRUCTURED if has_rag_data else QueryType.GENERAL
        
        # RULE 2: If entities found but no structured data, try RAG
        elif has_rag_data and entities:
            result['route'] = QueryType.UNSTRUCTURED
            result['reasoning'].append("Entities found but no structured data")
            result['fallback'] = QueryType.GENERAL
        
        # RULE 3: Explanation query with RAG data
        elif has_rag_data and not is_data:
            result['route'] = QueryType.UNSTRUCTURED
            result['reasoning'].append("Explanation query detected")
            result['fallback'] = QueryType.GENERAL
        
        # RULE 4: If structured data exists but not clearly a data query, try hybrid
        elif has_structured_data and has_rag_data:
            result['route'] = QueryType.HYBRID
            result['reasoning'].append("Ambiguous query - trying both sources")
            result['fallback'] = QueryType.GENERAL
        
        # RULE 5: Default to whatever we have
        elif has_structured_data:
            result['route'] = QueryType.STRUCTURED
            result['reasoning'].append("Only structured data available - trying SQL")
            result['fallback'] = QueryType.GENERAL
        
        elif has_rag_data:
            result['route'] = QueryType.UNSTRUCTURED
            result['reasoning'].append("Only RAG data available")
            result['fallback'] = QueryType.GENERAL
        
        else:
            result['route'] = QueryType.GENERAL
            result['reasoning'].append("No project data - using Claude's knowledge")
            result['fallback'] = None
        
        logger.info(f"[ROUTING] {query[:50]}... -> {result['route'].value} ({', '.join(result['reasoning'])})")
        
        return result
    
    def learn_from_success(self, query: str, route: QueryType, entities: List[str]):
        """Record successful routing for future learning"""
        query_lower = query.lower()
        
        # Store query pattern
        key_words = [w for w in query_lower.split() if len(w) > 3]
        pattern = ' '.join(sorted(key_words[:5]))
        
        if pattern not in self.learned_patterns['queries']:
            self.learned_patterns['queries'][pattern] = {
                'route': route.value,
                'entities': entities,
                'success_count': 0
            }
        
        self.learned_patterns['queries'][pattern]['success_count'] += 1
        self._save_learned_patterns()
    
    def learn_from_correction(self, query: str, wrong_route: QueryType, correct_route: QueryType):
        """Learn from user corrections"""
        query_lower = query.lower()
        key_words = [w for w in query_lower.split() if len(w) > 3]
        pattern = ' '.join(sorted(key_words[:5]))
        
        self.learned_patterns['queries'][pattern] = {
            'route': correct_route.value,
            'corrected_from': wrong_route.value,
            'success_count': 1
        }
        self._save_learned_patterns()
        logger.info(f"[LEARNING] Corrected routing: {wrong_route.value} -> {correct_route.value}")


def build_sql_prompt(query: str, schema: Dict, entities: List[Dict] = None) -> str:
    """
    Build a prompt for Claude to generate SQL.
    Include full schema context for intelligent query generation.
    """
    tables_info = []
    
    for table_name, table_data in schema.get('tables', {}).items():
        columns = table_data.get('columns', [])
        col_names = [c.get('name', c) if isinstance(c, dict) else c for c in columns]
        row_count = table_data.get('row_count', 'unknown')
        
        tables_info.append(f"""
Table: {table_name}
Columns: {', '.join(col_names)}
Rows: {row_count}
""")
    
    schema_text = '\n'.join(tables_info)
    
    entity_hint = ""
    if entities:
        entity_types = [e['type'] for e in entities]
        entity_hint = f"\nDetected entities in query: {', '.join(entity_types)}"
    
    prompt = f"""Generate a SQL query for DuckDB to answer this question.

AVAILABLE SCHEMA:
{schema_text}
{entity_hint}

USER QUESTION: {query}

RULES:
1. Return ONLY the SQL query, no explanation
2. Use exact table and column names from schema
3. Use ILIKE for case-insensitive text matching
4. LIMIT 1000 unless user asks for specific count
5. For "list" queries, SELECT DISTINCT on relevant columns
6. For "how many" queries, use COUNT(*)
7. If multiple tables could answer, pick the most relevant one
8. If unsure which column, include multiple relevant columns

SQL:"""
    
    return prompt


# Singleton instance
_router: Optional[IntelligentQueryRouter] = None

def get_query_router() -> IntelligentQueryRouter:
    """Get or create singleton router"""
    global _router
    if _router is None:
        _router = IntelligentQueryRouter()
    return _router


def detect_query_type(
    query: str,
    has_structured: bool = False,
    has_rag: bool = False,
    tables: List[str] = None
) -> Dict[str, Any]:
    """Convenience function for query routing"""
    router = get_query_router()
    return router.route_query(query, has_structured, has_rag, tables)
