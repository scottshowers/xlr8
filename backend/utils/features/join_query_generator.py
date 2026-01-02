"""
XLR8 Join Query Generator
=========================

Generates SQL with JOINs for multi-table queries.

When to use JOINs:
- User explicitly asks to combine data from multiple sources
- Query references columns from different tables
- Query asks for enriched/detailed data (employee with department name)

When NOT to use JOINs:
- Simple counts, lists, aggregations from single table
- When relationships aren't confident enough
- When tables have no common key

This is a focused module that handles ONLY join queries.
Simple queries still go through sql_generator.py.

Author: XLR8 Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class JoinQueryGenerator:
    """
    Generate SQL queries with JOINs using detected relationships.
    
    Works with project_intelligence relationships to know how to join tables.
    """
    
    # Patterns indicating user wants joined/enriched data
    JOIN_INTENT_PATTERNS = [
        r'\bwith\s+(their|the)\s+\w+\s+name',     # "employees with their department name"
        r'\bincluding\s+\w+\s+(name|description)', # "including location name"
        r'\bshow\s+\w+\s+details',                 # "show employee details"
        r'\bfull\s+(details|information)',         # "full details"
        r'\benriched?\b',                          # "enriched data"
        r'\bfrom\s+(\w+)\s+and\s+(\w+)',          # "from employees and departments"
        r'\bjoin\s+with\b',                        # "join with"
        r'\bcombine\s+\w+\s+(with|and)',          # "combine employees with departments"
        r'\bcross.?reference',                     # "cross-reference"
    ]
    
    def __init__(
        self,
        structured_handler=None,
        relationships: List = None,
        schema: Dict = None
    ):
        """
        Initialize join query generator.
        
        Args:
            structured_handler: DuckDB handler
            relationships: List of Relationship objects from project_intelligence
            schema: Schema with table info
        """
        self.handler = structured_handler
        self.relationships = relationships or []
        self.schema = schema or {}
    
    def needs_join(self, question: str, selected_tables: List[Dict]) -> bool:
        """
        Detect if a query needs multi-table JOIN.
        
        Args:
            question: User's question
            selected_tables: Tables selected by TableSelector
            
        Returns:
            True if JOIN query should be generated
        """
        q_lower = question.lower()
        
        # Check for explicit join intent patterns
        for pattern in self.JOIN_INTENT_PATTERNS:
            if re.search(pattern, q_lower):
                logger.info(f"[JOIN-GEN] Join intent detected: {pattern}")
                return True
        
        # Check if question mentions columns from multiple tables
        if len(selected_tables) > 1:
            # Extract mentioned column-like words
            words = set(re.findall(r'\b([a-z_]+)\b', q_lower))
            
            tables_with_matches = 0
            for table in selected_tables:
                columns = [c.lower() for c in table.get('columns', [])]
                if any(w in columns or any(w in c for c in columns) for w in words):
                    tables_with_matches += 1
            
            if tables_with_matches > 1:
                logger.info(f"[JOIN-GEN] Multiple tables have matching columns")
                return True
        
        return False
    
    def find_join_path(
        self,
        table_a: str,
        table_b: str
    ) -> Optional[Tuple[str, str, str, str]]:
        """
        Find how to join two tables using relationships.
        
        Args:
            table_a: First table name
            table_b: Second table name
            
        Returns:
            Tuple of (table_a_col, table_b_col, join_type, confidence) or None
        """
        for rel in self.relationships:
            # Direct relationship A -> B
            if (rel.from_table.lower() == table_a.lower() and 
                rel.to_table.lower() == table_b.lower()):
                return (rel.from_column, rel.to_column, 'LEFT JOIN', rel.confidence)
            
            # Reverse relationship B -> A
            if (rel.from_table.lower() == table_b.lower() and 
                rel.to_table.lower() == table_a.lower()):
                return (rel.to_column, rel.from_column, 'LEFT JOIN', rel.confidence)
        
        # Try to find common key columns
        return self._find_common_key(table_a, table_b)
    
    def _find_common_key(
        self,
        table_a: str,
        table_b: str
    ) -> Optional[Tuple[str, str, str, float]]:
        """
        Find common key columns between tables.
        
        Uses column name matching when no explicit relationship exists.
        """
        if not self.handler or not self.handler.conn:
            return None
        
        try:
            # Get columns for both tables
            cols_a = [row[0] for row in 
                     self.handler.conn.execute(f'DESCRIBE "{table_a}"').fetchall()]
            cols_b = [row[0] for row in 
                     self.handler.conn.execute(f'DESCRIBE "{table_b}"').fetchall()]
            
            # Key column patterns (higher priority)
            key_patterns = [
                'employee_id', 'emp_id', 'empid',
                'company_code', 'location_code', 'dept_code', 'department_code',
                'earning_code', 'deduction_code', 'tax_code',
                'code', 'id', 'key', 'number'
            ]
            
            # Check for exact matches first
            for col_a in cols_a:
                for col_b in cols_b:
                    if col_a.lower() == col_b.lower():
                        # Higher confidence for key-like columns
                        is_key = any(p in col_a.lower() for p in key_patterns)
                        confidence = 0.9 if is_key else 0.6
                        return (col_a, col_b, 'LEFT JOIN', confidence)
            
            # Check for semantic matches (employee_id ↔ emp_id)
            for col_a in cols_a:
                for col_b in cols_b:
                    if self._columns_match_semantically(col_a, col_b):
                        return (col_a, col_b, 'LEFT JOIN', 0.7)
            
            return None
            
        except Exception as e:
            logger.warning(f"[JOIN-GEN] Error finding common key: {e}")
            return None
    
    def _columns_match_semantically(self, col_a: str, col_b: str) -> bool:
        """Check if two column names refer to the same concept."""
        a_lower = col_a.lower()
        b_lower = col_b.lower()
        
        # Synonyms
        synonyms = [
            {'employee_id', 'emp_id', 'empid', 'ee_id', 'employee_number'},
            {'company_code', 'co_code', 'company'},
            {'location_code', 'loc_code', 'location'},
            {'department_code', 'dept_code', 'department'},
        ]
        
        for group in synonyms:
            if a_lower in group and b_lower in group:
                return True
            if any(s in a_lower for s in group) and any(s in b_lower for s in group):
                return True
        
        return False
    
    def generate(
        self,
        question: str,
        primary_table: Dict,
        join_tables: List[Dict],
        columns_to_select: List[str] = None
    ) -> Optional[Dict]:
        """
        Generate a JOIN query.
        
        Args:
            question: User's question
            primary_table: Main table to query from
            join_tables: Tables to join with
            columns_to_select: Specific columns to select (or None for smart selection)
            
        Returns:
            Dict with sql, tables, columns or None
        """
        primary_name = primary_table.get('table_name', '')
        if not primary_name:
            return None
        
        logger.info(f"[JOIN-GEN] Generating JOIN: {primary_name} with {len(join_tables)} tables")
        
        # Build SELECT columns
        select_cols = []
        if columns_to_select:
            select_cols = columns_to_select
        else:
            # Smart selection - include key columns from primary + description columns from joins
            primary_cols = primary_table.get('columns', [])[:10]
            for col in primary_cols:
                select_cols.append(f'"{primary_name}"."{col}"')
            
            for jt in join_tables:
                jt_name = jt.get('table_name', '')
                jt_cols = jt.get('columns', [])
                # Include description/name columns from join tables
                for col in jt_cols:
                    if any(x in col.lower() for x in ['name', 'description', 'desc', 'title']):
                        select_cols.append(f'"{jt_name}"."{col}" AS "{jt_name}_{col}"')
        
        if not select_cols:
            select_cols = [f'"{primary_name}".*']
        
        # Build JOINs
        join_clauses = []
        for jt in join_tables:
            jt_name = jt.get('table_name', '')
            join_info = self.find_join_path(primary_name, jt_name)
            
            if join_info:
                col_a, col_b, join_type, confidence = join_info
                join_clauses.append(
                    f'{join_type} "{jt_name}" ON "{primary_name}"."{col_a}" = "{jt_name}"."{col_b}"'
                )
                logger.info(f"[JOIN-GEN] Added join: {primary_name}.{col_a} = {jt_name}.{col_b} ({confidence})")
            else:
                logger.warning(f"[JOIN-GEN] Could not find join path to {jt_name}")
        
        if not join_clauses:
            logger.warning("[JOIN-GEN] No valid joins found")
            return None
        
        # Build SQL
        select_str = ',\n  '.join(select_cols)
        join_str = '\n'.join(join_clauses)
        
        sql = f'''SELECT
  {select_str}
FROM "{primary_name}"
{join_str}
LIMIT 1000'''
        
        # Parse question for filters
        where_clause = self._extract_filters(question, primary_table)
        if where_clause:
            sql = sql.replace('LIMIT 1000', f'WHERE {where_clause}\nLIMIT 1000')
        
        return {
            'sql': sql,
            'tables': [primary_name] + [jt.get('table_name', '') for jt in join_tables],
            'join_type': 'multi-table',
            'columns': select_cols
        }
    
    def _extract_filters(self, question: str, table: Dict) -> Optional[str]:
        """Extract WHERE clause filters from question."""
        # This is a simplified filter extraction
        # Full implementation would use the value-based filter detection from sql_generator
        
        filters = []
        q_lower = question.lower()
        
        # Status filter
        if 'active' in q_lower and 'status' in ' '.join(table.get('columns', [])).lower():
            filters.append("status = 'A'")
        elif 'terminated' in q_lower:
            filters.append("status = 'T'")
        
        # Limit patterns
        top_match = re.search(r'\btop\s+(\d+)\b', q_lower)
        if top_match:
            # Will be handled by LIMIT clause
            pass
        
        return ' AND '.join(filters) if filters else None


def get_join_generator(
    structured_handler=None,
    relationships: List = None,
    schema: Dict = None
) -> JoinQueryGenerator:
    """Get or create a JoinQueryGenerator instance."""
    return JoinQueryGenerator(structured_handler, relationships, schema)
