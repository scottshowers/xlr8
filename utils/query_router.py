"""
Query Router - Smart Query Detection and Routing
=================================================

Detects whether a query needs:
1. Structured data (SQL via DuckDB) - counting, listing, aggregations
2. Unstructured data (RAG via ChromaDB) - explanations, concepts, docs
3. Both - mixed queries requiring data + knowledge

Author: XLR8 Team
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    STRUCTURED = "structured"      # SQL query needed
    UNSTRUCTURED = "unstructured"  # RAG search needed
    HYBRID = "hybrid"              # Both needed
    GENERAL = "general"            # Just Claude's knowledge


class QueryRouter:
    """
    Routes queries to appropriate data sources.
    """
    
    # Patterns that indicate structured data queries (need SQL)
    STRUCTURED_PATTERNS = [
        # Counting/aggregation
        r'\bhow many\b', r'\bcount\b', r'\btotal\b', r'\bsum\b',
        r'\baverage\b', r'\bmean\b', r'\bmedian\b',
        r'\bminimum\b', r'\bmaximum\b', r'\bmin\b', r'\bmax\b',
        
        # Listing - EXPANDED to catch more variations
        r'\blist\b', r'\bshow\b', r'\bgive\s+me\b', r'\bget\b',
        r'\bwhat\s+are\s+(the|all)?\b', r'\bwhat\s+\w+\s+are\s+there\b',
        r'\bwhich\b', r'\bwho\s+(has|have|is|are)\b',
        r'\bdisplay\b', r'\bprint\b', r'\boutput\b',
        
        # Table/sheet references - trigger structured
        r'\b(in|from)\s+(the\s+)?\w+\s+(table|sheet)\b',
        r'\b\w+\s+table\b', r'\b\w+\s+sheet\b',
        
        # Filtering
        r'\bwhere\b', r'\bwith\b.*\b(of|=|equal)\b',
        r'\bfilter\b', r'\bonly\b', r'\bexclude\b',
        
        # Grouping
        r'\bgroup\s*by\b', r'\bper\s+\w+\b',
        r'\bby\s+(department|location|status|type|employee|pay\s*group)\b',
        r'\bbroken?\s*(down|out)\s+by\b',
        
        # Specific data entities - any mention triggers structured
        r'\bemployees?\b', r'\bearnings?\b', r'\bdeductions?\b',
        r'\bjob\s*codes?\b', r'\bdepartments?\b', r'\blocations?\b',
        r'\bpay\s*groups?\b', r'\btax\s*groups?\b', r'\bbenefits?\b',
        r'\bsalary\b', r'\bwages?\b', r'\brates?\b',
        r'\bearning\s*groups?\b', r'\bdeduction\s*groups?\b',
        
        # Comparisons
        r'\bgreater\s+than\b', r'\bless\s+than\b',
        r'\bmore\s+than\b', r'\bfewer\s+than\b',
        r'\bbetween\b.*\band\b', r'\babove\b', r'\bbelow\b',
        
        # Export/download
        r'\bexport\b', r'\bdownload\b', r'\bsave\s+to\b',
        r'\bcreate\s+(a\s+)?(report|spreadsheet|excel|csv)\b',
        
        # Direct SQL
        r'\bselect\b', r'\bfrom\b.*\bwhere\b',
    ]
    
    # Patterns that indicate unstructured/knowledge queries (need RAG or Claude)
    UNSTRUCTURED_PATTERNS = [
        # Explanations
        r'\bwhat\s+(does|is)\s+\w+\s+mean\b',
        r'\bexplain\b', r'\bdescribe\b', r'\btell\s+me\s+about\b',
        r'\bwhat\s+is\s+(a|an|the)\b',
        
        # How-to
        r'\bhow\s+(do|can|should|to)\b',
        r'\bwhat\s+should\b', r'\bbest\s+practice\b',
        
        # Why questions
        r'\bwhy\s+(is|are|do|does|would|should)\b',
        
        # Recommendations
        r'\brecommend\b', r'\bsuggest\b', r'\badvise\b',
        
        # Comparisons of concepts
        r'\bdifference\s+between\b', r'\bcompare\b.*\b(to|with|and)\b',
        
        # Process/procedure
        r'\bprocess\b', r'\bprocedure\b', r'\bworkflow\b', r'\bsteps?\b',
        
        # Configuration help
        r'\bhow\s+to\s+configure\b', r'\bset\s*up\b', r'\bconfiguration\b',
    ]
    
    # Patterns that indicate hybrid queries (need both)
    HYBRID_INDICATORS = [
        r'\band\s+(explain|tell|describe)\b',
        r'\b(along|together)\s+with\b',
        r'\bwith\s+(their|its)\s+\w+\s+(and|,)\b',  # "with their birthdate and..."
        r'\bthen\s+(explain|describe|tell)\b',
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self.structured_regex = [re.compile(p, re.IGNORECASE) for p in self.STRUCTURED_PATTERNS]
        self.unstructured_regex = [re.compile(p, re.IGNORECASE) for p in self.UNSTRUCTURED_PATTERNS]
        self.hybrid_regex = [re.compile(p, re.IGNORECASE) for p in self.HYBRID_INDICATORS]
    
    def detect_query_type(self, query: str) -> Tuple[QueryType, Dict[str, Any]]:
        """
        Detect the type of query and return routing info.
        
        Returns:
            (QueryType, metadata dict with details)
        """
        query_lower = query.lower()
        
        # Count pattern matches
        structured_matches = sum(1 for r in self.structured_regex if r.search(query))
        unstructured_matches = sum(1 for r in self.unstructured_regex if r.search(query))
        hybrid_matches = sum(1 for r in self.hybrid_regex if r.search(query))
        
        metadata = {
            'structured_score': structured_matches,
            'unstructured_score': unstructured_matches,
            'hybrid_indicators': hybrid_matches,
            'detected_entities': self._extract_entities(query)
        }
        
        # Decision logic
        if hybrid_matches > 0 and structured_matches > 0 and unstructured_matches > 0:
            query_type = QueryType.HYBRID
        elif structured_matches > unstructured_matches and structured_matches >= 2:
            query_type = QueryType.STRUCTURED
        elif unstructured_matches > structured_matches and unstructured_matches >= 2:
            query_type = QueryType.UNSTRUCTURED
        elif structured_matches > 0:
            query_type = QueryType.STRUCTURED
        elif unstructured_matches > 0:
            query_type = QueryType.UNSTRUCTURED
        else:
            query_type = QueryType.GENERAL
        
        metadata['query_type'] = query_type.value
        
        logger.info(f"Query routing: {query_type.value} (structured={structured_matches}, unstructured={unstructured_matches})")
        
        return query_type, metadata
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract relevant entities from the query"""
        entities = {
            'columns': [],
            'tables': [],
            'values': []
        }
        
        # Common column references
        column_patterns = [
            (r'\b(birth\s*date|dob|date\s*of\s*birth)\b', 'birthdate'),
            (r'\b(hire\s*date|doh|date\s*of\s*hire|start\s*date)\b', 'hire_date'),
            (r'\b(term\s*date|termination\s*date)\b', 'term_date'),
            (r'\b(job\s*code|position\s*code)\b', 'job_code'),
            (r'\b(department|dept)\b', 'department'),
            (r'\b(employee\s*id|emp\s*id|ee\s*id)\b', 'employee_id'),
            (r'\b(earning\s*code|earnings?\s*type)\b', 'earning_code'),
            (r'\b(filing\s*status|tax\s*status)\b', 'filing_status'),
            (r'\b(first\s*name|fname)\b', 'first_name'),
            (r'\b(last\s*name|lname|surname)\b', 'last_name'),
            (r'\b(ssn|social\s*security)\b', 'ssn'),
            (r'\b(salary|pay\s*rate|hourly\s*rate)\b', 'pay_rate'),
        ]
        
        for pattern, normalized in column_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                entities['columns'].append(normalized)
        
        # Look for quoted values or specific codes
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        entities['values'].extend(quoted)
        
        # Look for uppercase codes (like REG, OT, BONUS)
        codes = re.findall(r'\b([A-Z]{2,10})\b', query)
        entities['values'].extend(codes)
        
        return entities
    
    def build_sql_prompt(self, query: str, schema: Dict[str, Any]) -> str:
        """
        Build a prompt for Claude to generate SQL.
        Includes schema info so Claude knows what tables/columns exist.
        """
        tables_desc = []
        for table in schema.get('tables', []):
            cols = [c['name'] for c in table.get('columns', [])]
            keys = table.get('likely_keys', [])
            tables_desc.append(
                f"Table: {table['table_name']}\n"
                f"  Source: {table['file']} → {table['sheet']}\n"
                f"  Columns: {', '.join(cols)}\n"
                f"  Rows: {table['row_count']}\n"
                f"  Likely join keys: {', '.join(keys) if keys else 'none detected'}"
            )
        
        prompt = f"""You are a SQL expert. Generate a DuckDB SQL query to answer this question.

AVAILABLE TABLES:
{chr(10).join(tables_desc)}

USER QUESTION: {query}

RULES:
1. Use only the tables and columns listed above
2. Table names are exact - use them as shown
3. For joins, use the likely join keys (usually employee_id or similar)
4. Return only the SQL query, no explanation
5. Use ILIKE for case-insensitive string matching
6. Limit results to 1000 rows max unless counting

SQL QUERY:"""
        
        return prompt
    
    def needs_export(self, query: str) -> bool:
        """Check if query requests data export"""
        export_patterns = [
            r'\bexport\b', r'\bdownload\b', r'\bsave\b',
            r'\bexcel\b', r'\bcsv\b', r'\bspreadsheet\b',
            r'\bcreate\s+(a\s+)?file\b'
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in export_patterns)


# Singleton
_router: Optional[QueryRouter] = None

def get_query_router() -> QueryRouter:
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router
