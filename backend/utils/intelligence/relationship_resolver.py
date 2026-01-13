"""
XLR8 Relationship Resolver - Evolution 10: Multi-Hop Relationships
===================================================================

Handles relationship chain navigation for queries like:
- "manager's department" → self-join: employee → supervisor_id → employee → department
- "employees in John's team" → filter on supervisor = John
- "location's regional manager" → multi-hop: location → manager_id → employee

ARCHITECTURE:
- Detects relationship patterns in queries (possessives, relationship keywords)
- Resolves relationship chains using _column_relationships metadata
- Generates proper self-join SQL with table aliases
- Handles both direct and multi-hop relationships

RELATIONSHIP TYPES:
- self_reference: supervisor_id → employee_number (same table)
- foreign_key: department_code → department_code (different tables)
- lookup: location_code → location_code (config lookup)
- hierarchy: org_level_1 → parent_org_level (hierarchical)

Author: XLR8 Team
Version: 1.0.0
Date: 2026-01-12
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import duckdb

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class RelationshipType(Enum):
    """Types of column relationships."""
    SELF_REFERENCE = "self_reference"  # supervisor_id → employee_id (same table)
    FOREIGN_KEY = "foreign_key"         # column → another table's column
    LOOKUP = "lookup"                   # code → config/lookup table
    HIERARCHY = "hierarchy"             # parent_id → child_id (tree structure)
    UNKNOWN = "unknown"


class RelationshipDirection(Enum):
    """Direction for traversing relationships."""
    FORWARD = "forward"   # employee → manager (up the chain)
    REVERSE = "reverse"   # manager → employees (down the chain)


@dataclass
class Relationship:
    """A detected relationship between columns."""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: RelationshipType
    semantic_meaning: str  # e.g., "supervisor", "manager", "parent_org"
    confidence: float = 0.9
    
    @property
    def is_self_reference(self) -> bool:
        """Check if this is a self-referential relationship."""
        return self.source_table == self.target_table


@dataclass
class RelationshipChain:
    """A chain of relationships to traverse."""
    relationships: List[Relationship]
    direction: RelationshipDirection
    final_target: str  # What we want at the end (e.g., "department")
    
    @property
    def hop_count(self) -> int:
        return len(self.relationships)


@dataclass
class MultiHopJoin:
    """SQL join information for multi-hop relationships."""
    table_aliases: Dict[str, str]  # table_name → alias (e.g., t0, t1_mgr)
    join_clauses: List[str]        # JOIN clause strings
    target_alias: str              # Alias for the final target table
    target_column: str             # Column to select from target


# =============================================================================
# RELATIONSHIP PATTERNS - Query Detection
# =============================================================================

# Possessive patterns: "X's Y" or "X' Y"
POSSESSIVE_PATTERN = re.compile(
    r"(\w+)(?:'s|')\s+(\w+(?:\s+\w+)?)",
    re.IGNORECASE
)

# Relationship keywords that indicate traversal
RELATIONSHIP_KEYWORDS = {
    # Supervisor/Manager relationships
    'manager': {'semantic': 'supervisor', 'direction': 'forward'},
    'supervisor': {'semantic': 'supervisor', 'direction': 'forward'},
    'boss': {'semantic': 'supervisor', 'direction': 'forward'},
    'leader': {'semantic': 'supervisor', 'direction': 'forward'},
    'direct report': {'semantic': 'supervisor', 'direction': 'reverse'},
    'reports to': {'semantic': 'supervisor', 'direction': 'forward'},
    'managed by': {'semantic': 'supervisor', 'direction': 'forward'},
    'leads': {'semantic': 'supervisor', 'direction': 'reverse'},
    'team': {'semantic': 'supervisor', 'direction': 'reverse'},
    
    # Organizational hierarchy
    'parent': {'semantic': 'parent_org', 'direction': 'forward'},
    'child': {'semantic': 'parent_org', 'direction': 'reverse'},
    'subsidiary': {'semantic': 'parent_org', 'direction': 'reverse'},
    'division': {'semantic': 'parent_org', 'direction': 'reverse'},
}

# Attribute mappings: what target attributes mean
TARGET_ATTRIBUTES = {
    'department': ['department_code', 'department', 'dept_code', 'dept', 'org_level_1', 'org_level_2', 'org_level_3', 'org_level'],
    'location': ['location_code', 'location', 'loc_code', 'work_location'],
    'job': ['job_code', 'job_title', 'position_code', 'job'],
    'salary': ['annual_salary', 'salary', 'pay_rate', 'rate', 'hourly_pay_rate', 'period_pay_rate'],
    'name': ['employee_name', 'full_name', 'name', 'first_name', 'last_name'],
    'email': ['email', 'email_address', 'work_email'],
    'phone': ['phone', 'phone_number', 'work_phone'],
    'state': ['stateprovince', 'state', 'state_code'],
    'company': ['company_code', 'company', 'org_code'],
}

# Self-reference column patterns (supervisor columns that reference employee columns)
SELF_REFERENCE_PATTERNS = [
    # Pattern: (supervisor_column_pattern, target_column_pattern, semantic_meaning)
    (r'supervisor.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
    (r'manager.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
    (r'reports.*to.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
    (r'alternate.*super.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'alternate_supervisor'),
    (r'primary.*super.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'primary_supervisor'),
    (r'direct.*report.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
    (r'parent.*(?:id|code)$', r'(?:id|code)$', 'parent_org'),
]


# =============================================================================
# RELATIONSHIP RESOLVER CLASS
# =============================================================================

class RelationshipResolver:
    """
    Resolves multi-hop relationships for queries.
    
    Usage:
        resolver = RelationshipResolver(conn, project)
        
        # Detect and store relationships at upload time
        resolver.detect_relationships(table_name)
        
        # At query time, find relationship chains
        chain = resolver.find_relationship_chain("manager", "department")
        
        # Generate SQL joins
        join_info = resolver.build_multi_hop_join(chain, primary_table)
    """
    
    def __init__(self, conn: duckdb.DuckDBPyConnection, project: str):
        self.conn = conn
        self.project = project.lower()
        self._ensure_tables()
        self._load_relationships()
    
    def _ensure_tables(self):
        """Create relationship tracking tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _column_relationships (
                project VARCHAR NOT NULL,
                source_table VARCHAR NOT NULL,
                source_column VARCHAR NOT NULL,
                target_table VARCHAR NOT NULL,
                target_column VARCHAR NOT NULL,
                relationship_type VARCHAR NOT NULL,
                semantic_meaning VARCHAR,
                confidence FLOAT DEFAULT 0.9,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (project, source_table, source_column, target_table, target_column)
            )
        """)
        
        try:
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_source 
                ON _column_relationships(project, source_table, source_column)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_semantic 
                ON _column_relationships(project, semantic_meaning)
            """)
        except Exception as e:
            logger.debug(f"Index creation note: {e}")
    
    def _load_relationships(self):
        """Load cached relationships from database."""
        self._relationships: List[Relationship] = []
        self._by_semantic: Dict[str, List[Relationship]] = {}
        self._by_table: Dict[str, List[Relationship]] = {}
        
        try:
            results = self.conn.execute("""
                SELECT source_table, source_column, target_table, target_column,
                       relationship_type, semantic_meaning, confidence
                FROM _column_relationships
                WHERE project = ?
            """, [self.project]).fetchall()
            
            for row in results:
                rel = Relationship(
                    source_table=row[0],
                    source_column=row[1],
                    target_table=row[2],
                    target_column=row[3],
                    relationship_type=RelationshipType(row[4]) if row[4] else RelationshipType.UNKNOWN,
                    semantic_meaning=row[5] or '',
                    confidence=row[6] or 0.9
                )
                self._relationships.append(rel)
                
                # Index by semantic meaning
                if rel.semantic_meaning:
                    if rel.semantic_meaning not in self._by_semantic:
                        self._by_semantic[rel.semantic_meaning] = []
                    self._by_semantic[rel.semantic_meaning].append(rel)
                
                # Index by source table
                if rel.source_table not in self._by_table:
                    self._by_table[rel.source_table] = []
                self._by_table[rel.source_table].append(rel)
            
            logger.info(f"[RELATIONSHIP] Loaded {len(self._relationships)} relationships for project {self.project}")
            
        except Exception as e:
            logger.warning(f"[RELATIONSHIP] Could not load relationships: {e}")
    
    # =========================================================================
    # RELATIONSHIP DETECTION (at upload time)
    # =========================================================================
    
    def detect_relationships(self, table_name: str) -> List[Relationship]:
        """
        Detect relationships in a table by analyzing column names and values.
        
        Called during column profiling to discover:
        - Self-referential columns (supervisor_id → employee_id)
        - Foreign key relationships (department_code → departments.code)
        
        Returns list of detected relationships.
        """
        detected = []
        
        try:
            # Get columns for this table
            columns = self.conn.execute("""
                SELECT column_name, semantic_type, inferred_type
                FROM _column_profiles
                WHERE LOWER(project) = ? AND table_name = ?
            """, [self.project, table_name]).fetchall()
            
            column_info = {row[0].lower(): {'semantic': row[1], 'type': row[2]} for row in columns}
            column_names = list(column_info.keys())
            
            # Check for self-reference patterns
            for source_col in column_names:
                for pattern, target_pattern, semantic in SELF_REFERENCE_PATTERNS:
                    if re.search(pattern, source_col, re.IGNORECASE):
                        # Find matching target column
                        for target_col in column_names:
                            if source_col != target_col and re.search(target_pattern, target_col, re.IGNORECASE):
                                rel = Relationship(
                                    source_table=table_name,
                                    source_column=source_col,
                                    target_table=table_name,
                                    target_column=target_col,
                                    relationship_type=RelationshipType.SELF_REFERENCE,
                                    semantic_meaning=semantic,
                                    confidence=0.85
                                )
                                detected.append(rel)
                                self._store_relationship(rel)
                                logger.info(f"[RELATIONSHIP] Detected self-reference: {table_name}.{source_col} → {target_col} ({semantic})")
                                break  # Found match, move to next source col
            
            # Check for foreign key relationships based on semantic types
            detected.extend(self._detect_foreign_keys(table_name, column_info))
            
        except Exception as e:
            logger.warning(f"[RELATIONSHIP] Error detecting relationships: {e}")
        
        return detected
    
    def _detect_foreign_keys(self, table_name: str, column_info: Dict) -> List[Relationship]:
        """Detect foreign key relationships based on semantic type matching."""
        detected = []
        
        try:
            # For each column with a semantic type, find matching columns in other tables
            for col_name, info in column_info.items():
                semantic = info.get('semantic')
                if not semantic:
                    continue
                
                # Skip employee identifiers (handled separately)
                if semantic in ('employee_number', 'employee_id'):
                    continue
                
                # Find other tables with matching semantic type
                matches = self.conn.execute("""
                    SELECT DISTINCT table_name, column_name
                    FROM _column_profiles
                    WHERE LOWER(project) = ? 
                      AND semantic_type = ?
                      AND table_name != ?
                    LIMIT 5
                """, [self.project, semantic, table_name]).fetchall()
                
                for target_table, target_col in matches:
                    # Check if this is a likely lookup relationship
                    # (e.g., personal.location_code → locations.location_code)
                    rel = Relationship(
                        source_table=table_name,
                        source_column=col_name,
                        target_table=target_table,
                        target_column=target_col,
                        relationship_type=RelationshipType.FOREIGN_KEY,
                        semantic_meaning=semantic,
                        confidence=0.7
                    )
                    detected.append(rel)
                    self._store_relationship(rel)
                    
        except Exception as e:
            logger.debug(f"[RELATIONSHIP] Foreign key detection note: {e}")
        
        return detected
    
    def _store_relationship(self, rel: Relationship):
        """Store a relationship in the database."""
        try:
            self.conn.execute("""
                INSERT INTO _column_relationships 
                (project, source_table, source_column, target_table, target_column,
                 relationship_type, semantic_meaning, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (project, source_table, source_column, target_table, target_column)
                DO UPDATE SET
                    relationship_type = EXCLUDED.relationship_type,
                    semantic_meaning = EXCLUDED.semantic_meaning,
                    confidence = EXCLUDED.confidence
            """, [
                self.project,
                rel.source_table,
                rel.source_column,
                rel.target_table,
                rel.target_column,
                rel.relationship_type.value,
                rel.semantic_meaning,
                rel.confidence
            ])
            self.conn.commit()
            
            # Update in-memory cache
            self._relationships.append(rel)
            if rel.semantic_meaning:
                if rel.semantic_meaning not in self._by_semantic:
                    self._by_semantic[rel.semantic_meaning] = []
                self._by_semantic[rel.semantic_meaning].append(rel)
                
        except Exception as e:
            logger.debug(f"[RELATIONSHIP] Store note: {e}")
    
    # =========================================================================
    # QUERY PATTERN DETECTION
    # =========================================================================
    
    def parse_relationship_query(self, question: str) -> Optional[Dict]:
        """
        Parse a query to detect relationship patterns.
        
        Returns dict with:
        - traversal_type: 'possessive', 'keyword', or None
        - source_entity: e.g., 'manager'
        - target_attribute: e.g., 'department'
        - direction: forward or reverse
        
        Examples:
        - "manager's department" → {'traversal_type': 'possessive', 'source_entity': 'manager', 'target_attribute': 'department'}
        - "employees who report to John" → {'traversal_type': 'keyword', 'source_entity': 'employees', 'filter': 'John'}
        """
        question_lower = question.lower()
        
        # Check for possessive patterns
        match = POSSESSIVE_PATTERN.search(question)
        if match:
            source = match.group(1).lower()
            target = match.group(2).lower()
            
            # Is the source a relationship keyword?
            if source in RELATIONSHIP_KEYWORDS:
                return {
                    'traversal_type': 'possessive',
                    'source_entity': source,
                    'target_attribute': target,
                    'semantic': RELATIONSHIP_KEYWORDS[source]['semantic'],
                    'direction': RELATIONSHIP_KEYWORDS[source]['direction'],
                    'original_match': match.group(0)
                }
            
            # Check if source is a name (likely "John's team")
            if source[0].isupper() or source.isalpha():
                # Could be a person's name
                return {
                    'traversal_type': 'named_possessive',
                    'source_entity': source,
                    'target_attribute': target,
                    'original_match': match.group(0)
                }
        
        # Check for relationship keywords in the query
        for keyword, info in RELATIONSHIP_KEYWORDS.items():
            if keyword in question_lower:
                return {
                    'traversal_type': 'keyword',
                    'keyword': keyword,
                    'semantic': info['semantic'],
                    'direction': info['direction']
                }
        
        return None
    
    # =========================================================================
    # RELATIONSHIP CHAIN BUILDING
    # =========================================================================
    
    def find_relationship_chain(self, 
                                from_semantic: str,
                                to_attribute: str,
                                from_table: str = None) -> Optional[RelationshipChain]:
        """
        Find a chain of relationships to traverse.
        
        Args:
            from_semantic: Starting relationship (e.g., 'supervisor')
            to_attribute: Target attribute (e.g., 'department')
            from_table: Optional starting table hint
            
        Returns:
            RelationshipChain if a path exists, None otherwise
        """
        # Find relationships with matching semantic meaning
        relationships = self._by_semantic.get(from_semantic, [])
        
        if not relationships:
            logger.warning(f"[RELATIONSHIP] No relationships found for semantic '{from_semantic}'")
            return None
        
        # Filter by table if specified
        if from_table:
            relationships = [r for r in relationships if r.source_table == from_table]
        
        if not relationships:
            return None
        
        # For self-reference relationships, we need to traverse to the target
        # and then access the attribute from the target record
        rel = relationships[0]  # Take first matching relationship
        
        # Check if target attribute exists in the target table
        target_column = self._find_target_column(rel.target_table, to_attribute)
        
        if target_column:
            return RelationshipChain(
                relationships=[rel],
                direction=RelationshipDirection.FORWARD,
                final_target=target_column
            )
        
        logger.warning(f"[RELATIONSHIP] Could not find '{to_attribute}' in {rel.target_table}")
        return None
    
    def _find_target_column(self, table: str, attribute: str) -> Optional[str]:
        """Find the actual column name for a target attribute."""
        # Get possible column patterns for this attribute
        patterns = TARGET_ATTRIBUTES.get(attribute.lower(), [attribute.lower()])
        
        try:
            # Get columns from the table
            columns = self.conn.execute("""
                SELECT column_name 
                FROM _column_profiles
                WHERE LOWER(project) = ? AND table_name = ?
            """, [self.project, table]).fetchall()
            
            column_names = [r[0].lower() for r in columns]
            
            # Check each pattern
            for pattern in patterns:
                for col in column_names:
                    if pattern in col or col in pattern:
                        return col
                        
        except Exception as e:
            logger.debug(f"[RELATIONSHIP] Column lookup note: {e}")
        
        return None
    
    # =========================================================================
    # SQL GENERATION FOR MULTI-HOP
    # =========================================================================
    
    def build_multi_hop_join(self,
                             chain: RelationshipChain,
                             primary_table: str,
                             primary_alias: str = 't0') -> MultiHopJoin:
        """
        Build SQL join clauses for a multi-hop relationship chain.
        
        For self-reference:
          SELECT t0.*, t1_mgr.department_code
          FROM employees t0
          JOIN employees t1_mgr ON t0.supervisor_id = t1_mgr.employee_number
        
        Args:
            chain: The relationship chain to traverse
            primary_table: The starting table
            primary_alias: Alias for the primary table (default 't0')
            
        Returns:
            MultiHopJoin with alias mapping and join clauses
        """
        aliases = {primary_table: primary_alias}
        join_clauses = []
        
        current_alias = primary_alias
        hop_num = 1
        
        for rel in chain.relationships:
            if rel.is_self_reference:
                # Self-join: same table, different alias
                new_alias = f"t{hop_num}_mgr"
                aliases[f"{rel.target_table}_hop{hop_num}"] = new_alias
                
                join_clause = (
                    f'JOIN "{rel.source_table}" {new_alias} '
                    f'ON {current_alias}."{rel.source_column}" = {new_alias}."{rel.target_column}"'
                )
                join_clauses.append(join_clause)
                current_alias = new_alias
                
            else:
                # Regular join: different tables
                new_alias = f"t{hop_num}"
                aliases[rel.target_table] = new_alias
                
                join_clause = (
                    f'JOIN "{rel.target_table}" {new_alias} '
                    f'ON {current_alias}."{rel.source_column}" = {new_alias}."{rel.target_column}"'
                )
                join_clauses.append(join_clause)
                current_alias = new_alias
            
            hop_num += 1
        
        return MultiHopJoin(
            table_aliases=aliases,
            join_clauses=join_clauses,
            target_alias=current_alias,
            target_column=chain.final_target
        )
    
    def generate_multi_hop_sql(self,
                               chain: RelationshipChain,
                               primary_table: str,
                               select_columns: List[str] = None,
                               where_conditions: List[str] = None,
                               limit: int = 100) -> str:
        """
        Generate complete SQL for a multi-hop query.
        
        Args:
            chain: Relationship chain to traverse
            primary_table: Starting table
            select_columns: Columns to select (default: primary.*, target_column)
            where_conditions: Additional WHERE conditions
            limit: Row limit
            
        Returns:
            Complete SQL query string
        """
        join_info = self.build_multi_hop_join(chain, primary_table)
        
        # Build SELECT clause
        primary_alias = join_info.table_aliases.get(primary_table, 't0')
        
        if select_columns:
            select_parts = []
            for col in select_columns:
                if '.' in col:
                    select_parts.append(col)
                else:
                    select_parts.append(f'{primary_alias}."{col}"')
            select_clause = ', '.join(select_parts)
        else:
            # Default: all primary columns + target column
            select_clause = (
                f'{primary_alias}.*, '
                f'{join_info.target_alias}."{join_info.target_column}" as mgr_{join_info.target_column}'
            )
        
        # Build FROM clause
        sql = f'SELECT {select_clause}\n'
        sql += f'FROM "{primary_table}" {primary_alias}\n'
        
        # Add JOINs
        for join_clause in join_info.join_clauses:
            sql += f'{join_clause}\n'
        
        # Add WHERE if any
        if where_conditions:
            sql += f'WHERE {" AND ".join(where_conditions)}\n'
        
        # Add LIMIT
        sql += f'LIMIT {limit}'
        
        return sql


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_resolver(conn: duckdb.DuckDBPyConnection, project: str) -> RelationshipResolver:
    """Get a relationship resolver instance."""
    return RelationshipResolver(conn, project)


def detect_multi_hop_query(question: str) -> Optional[Dict]:
    """
    Quick check if a query involves multi-hop relationships.
    
    Returns pattern info if detected, None otherwise.
    """
    resolver = RelationshipResolver.__new__(RelationshipResolver)
    return resolver.parse_relationship_query(question)
