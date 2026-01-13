"""
XLR8 Intelligent Scoping - The Consultant's First Move
=======================================================

Before answering ANY question, a world-class consultant:
1. Understands the data landscape
2. Knows where activity actually exists (not just config)
3. Scopes appropriately based on REALITY, not assumptions

This module queries the Context Graph to understand:
- What hubs are relevant to the question
- What values are ACTUALLY in use (not just configured)
- Where employees/transactions are concentrated
- What meaningful segmentation exists

Then it either:
- Asks a smart clarifying question (showing we know their data)
- Or proceeds with intelligent defaults

The magic: We show them we understand their data before they tell us.

Deploy to: backend/utils/intelligent_scoping.py
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Known employee/person identifier columns - used for DISTINCT counting
EMPLOYEE_IDENTIFIER_COLUMNS = {
    'employee_number', 'person_number', 'worker_id', 'employee_id',
    'person_id', 'emp_no', 'empno', 'emp_id', 'worker_number',
    'employee_key', 'person_key', 'worker_key'
}


@dataclass
class ScopeSegment:
    """A meaningful segment in the data."""
    dimension: str          # e.g., "country", "company", "org_level_1"
    value: str              # e.g., "US", "ACME Corp"
    display_name: str       # e.g., "United States", "ACME Corporation"
    employee_count: int     # Active employees in this segment
    item_count: int         # Config items (deductions, earnings, etc.)
    unused_count: int       # Configured but not used - GAP
    coverage_pct: float     # % of config in use


@dataclass
class ScopeAnalysis:
    """Result of analyzing the data scope for a question."""
    needs_clarification: bool
    question_domain: str           # deductions, earnings, employees, etc.
    relevant_hubs: List[str]       # Hub columns relevant to question
    segments: List[ScopeSegment]   # Meaningful segments found
    total_items: int               # Total across all segments
    total_employees: int           # Total employees affected
    suggested_question: str        # Clarifying question if needed
    can_proceed: bool              # True if we can answer without clarification
    default_scope: Dict[str, str]  # Default filters if proceeding


@dataclass
class HubUsage:
    """Usage statistics for a hub."""
    hub_column: str
    hub_table: str
    semantic_type: str
    total_values: int           # Values in hub (config)
    used_values: int            # Values with spokes (in use)
    unused_values: int          # Values with no spokes (gaps)
    employee_count: int         # Total employees connected
    by_value: Dict[str, int]    # Employee count per value


class IntelligentScoping:
    """
    Analyzes the data landscape before answering questions.
    
    Uses Context Graph to understand:
    - What's configured vs what's actually used
    - Where employees are concentrated
    - What segmentation makes sense
    
    CRITICAL: This is VENDOR/PRODUCT AGNOSTIC.
    We discover segmentation dimensions from the DATA, not hardcoded lists.
    Works for UKG, Workday, SAP, or any system with hub/spoke patterns.
    """
    
    # Domain keywords to semantic type mappings (product-agnostic)
    DOMAIN_PATTERNS = {
        'deduction': ['deduction', 'benefit', 'garnish', '401k', 'insurance', 'withhold'],
        'earning': ['earning', 'wage', 'salary', 'bonus', 'overtime', 'pay code', 'compensation'],
        'tax': ['tax', 'withhold', 'sui', 'sdi', 'fica', 'w2', 'w4', 'federal', 'state tax'],
        'employee': ['employee', 'worker', 'staff', 'headcount', 'roster', 'person', 'associate'],
        'organization': ['company', 'entity', 'legal entity', 'org', 'department', 'division', 'cost center'],
        'payroll': ['pay group', 'pay frequency', 'payroll', 'pay period', 'pay cycle'],
        'job': ['job', 'position', 'title', 'role', 'grade', 'classification'],
        'location': ['location', 'site', 'work location', 'office', 'address', 'geography'],
        'project': ['project', 'project code', 'task', 'assignment'],
        'time': ['time', 'hours', 'attendance', 'schedule', 'shift'],
    }
    
    # Column patterns that indicate segmentation potential (product-agnostic)
    SEGMENTATION_PATTERNS = [
        # Geography
        ('country', 'Country'),
        ('region', 'Region'),
        ('state', 'State'),
        # Organization
        ('company', 'Company'),
        ('entity', 'Entity'),
        ('division', 'Division'),
        ('department', 'Department'),
        ('org_level', 'Org Level'),
        ('cost_center', 'Cost Center'),
        ('business_unit', 'Business Unit'),
        # Payroll
        ('pay_group', 'Pay Group'),
        ('pay_frequency', 'Pay Frequency'),
        # Status
        ('status', 'Status'),
        ('type', 'Type'),
    ]
    
    # Thresholds
    MIN_SEGMENT_SIZE = 10          # Minimum employees to be a meaningful segment
    MIN_SEGMENTS_TO_ASK = 2        # Need at least 2 segments to ask clarification
    MAX_SEGMENTS_TO_SHOW = 5       # Don't overwhelm with too many options
    MIN_HUB_SPOKES = 3             # Minimum spokes for a hub to be segmentation candidate
    
    def __init__(self, project_name: str, structured_handler=None):
        """
        Initialize with project context.
        
        Args:
            project_name: Project code
            structured_handler: DuckDB handler for queries
        """
        self.project_name = project_name
        self.handler = structured_handler
        self._context_graph = None
        self._hub_usage_cache = {}
    
    def analyze(self, question: str, context: Dict = None) -> ScopeAnalysis:
        """
        Analyze the question and data to determine scoping.
        
        Args:
            question: User's question
            context: Additional context (schema, etc.)
            
        Returns:
            ScopeAnalysis with scoping recommendation
        """
        logger.warning(f"[SCOPE] Analyzing: {question[:60]}...")
        
        # Step 1: Detect question domain
        domain = self._detect_domain(question)
        logger.warning(f"[SCOPE] Domain detected: {domain}")
        
        # Step 2: Get relevant hubs for this domain
        relevant_hubs = self._get_relevant_hubs(domain, context)
        logger.warning(f"[SCOPE] Relevant hubs: {relevant_hubs}")
        
        # Step 3: Analyze segmentation (where are the employees?)
        segments = self._analyze_segments(domain, relevant_hubs, context)
        logger.warning(f"[SCOPE] Segments found: {len(segments)}")
        
        # Step 4: Decide if clarification needed
        needs_clarification = self._should_ask_clarification(segments)
        
        # Step 5: Build the analysis result
        total_items = sum(s.item_count for s in segments)
        total_employees = sum(s.employee_count for s in segments)
        
        suggested_question = ""
        if needs_clarification:
            suggested_question = self._build_clarifying_question(domain, segments)
        
        # Default scope (if proceeding without clarification)
        default_scope = {}
        if not needs_clarification and segments:
            # Use the largest segment as default, or "all" if similar sizes
            largest = max(segments, key=lambda s: s.employee_count)
            if largest.employee_count > total_employees * 0.8:
                default_scope[largest.dimension] = largest.value
        
        return ScopeAnalysis(
            needs_clarification=needs_clarification,
            question_domain=domain,
            relevant_hubs=relevant_hubs,
            segments=segments,
            total_items=total_items,
            total_employees=total_employees,
            suggested_question=suggested_question,
            can_proceed=not needs_clarification,
            default_scope=default_scope
        )
    
    def _detect_domain(self, question: str) -> str:
        """
        Detect the domain of the question.
        
        VENDOR-AGNOSTIC: Uses generic domain patterns, not product-specific terms.
        """
        q_lower = question.lower()
        
        # Check each domain's keywords from class patterns
        for domain, keywords in self.DOMAIN_PATTERNS.items():
            if any(kw in q_lower for kw in keywords):
                return domain
        
        return 'general'
    
    def _get_relevant_hubs(self, domain: str, context: Dict = None) -> List[str]:
        """
        Get hub columns relevant to this domain.
        
        VENDOR-AGNOSTIC: Discovers hubs from Context Graph, not hardcoded lists.
        """
        hubs = []
        
        # First, try to get hubs from Context Graph
        if self.handler:
            discovered_hubs = self._discover_hubs_from_graph()
            if discovered_hubs:
                hubs.extend(discovered_hubs)
        
        return list(set(hubs))
    
    def _discover_hubs_from_graph(self) -> List[str]:
        """
        Discover hub columns from Context Graph.
        
        Returns columns that:
        1. Are marked as hubs (is_hub=True)
        2. Have multiple spokes (connected to multiple tables)
        3. Are good segmentation candidates
        """
        hubs = []
        
        try:
            # Query _column_mappings for hub columns
            # Schema: original_column (not column_name), semantic_type, is_hub
            sql = """
                SELECT DISTINCT original_column, semantic_type, 
                       COUNT(*) as table_count
                FROM _column_mappings 
                WHERE is_hub = TRUE OR is_hub = 1
                GROUP BY original_column, semantic_type
                ORDER BY table_count DESC
            """
            rows = self.handler.query(sql)
            
            for row in rows:
                col = row.get('original_column', '')
                count = row.get('table_count', 0)
                if col and count >= self.MIN_HUB_SPOKES:
                    hubs.append(col)
                    
        except Exception as e:
            logger.debug(f"[SCOPE] Could not query hubs from graph: {e}")
            # Fallback to discovering from column names
            hubs = self._discover_hubs_from_patterns()
        
        return hubs
    
    def _discover_hubs_from_patterns(self) -> List[str]:
        """
        Fallback: Discover potential hub columns from column name patterns.
        Used when Context Graph isn't available.
        """
        hubs = []
        
        try:
            # Query all columns that look like segmentation candidates
            # Schema uses original_column, not column_name
            patterns = [p[0] for p in self.SEGMENTATION_PATTERNS]
            pattern_clause = " OR ".join([f"LOWER(original_column) LIKE '%{p}%'" for p in patterns])
            
            sql = f"""
                SELECT DISTINCT original_column
                FROM _column_mappings 
                WHERE {pattern_clause}
            """
            rows = self.handler.query(sql)
            hubs = [r.get('original_column') for r in rows if r.get('original_column')]
            
        except Exception as e:
            logger.debug(f"[SCOPE] Could not discover hubs from patterns: {e}")
        
        return hubs
    
    def _analyze_segments(self, domain: str, relevant_hubs: List[str], 
                         context: Dict = None) -> List[ScopeSegment]:
        """
        Analyze data segments based on discovered dimensions.
        
        VENDOR-AGNOSTIC: Uses hub discovery, not hardcoded column names.
        """
        segments = []
        
        if not self.handler:
            logger.warning("[SCOPE] No handler available for segment analysis")
            return segments
        
        # Discover segmentation dimensions from the data
        segmentation_dims = self._discover_segmentation_dimensions()
        
        if not segmentation_dims:
            logger.warning("[SCOPE] No segmentation dimensions discovered")
            return segments
        
        # Try each discovered dimension
        for dim_column, dim_name in segmentation_dims:
            dim_segments = self._query_segment_stats(dim_column, dim_name, domain)
            if dim_segments and len(dim_segments) >= self.MIN_SEGMENTS_TO_ASK:
                # Found meaningful segmentation
                segments = dim_segments[:self.MAX_SEGMENTS_TO_SHOW]
                break
        
        return segments
    
    def _discover_segmentation_dimensions(self) -> List[Tuple[str, str]]:
        """
        Discover which columns are good for segmentation.
        
        VENDOR-AGNOSTIC: Looks for columns that:
        1. Appear in multiple tables (common dimension)
        2. Have low cardinality (meaningful grouping)
        3. Match segmentation patterns (country, company, etc.)
        """
        dimensions = []
        
        try:
            # Find columns that appear in multiple tables and have low cardinality
            # Schema: _column_mappings has original_column, table_name
            # Schema: _column_profiles has column_name (different!), distinct_count
            sql = """
                SELECT 
                    cm.original_column,
                    COUNT(DISTINCT cm.table_name) as table_count
                FROM _column_mappings cm
                WHERE cm.original_column IS NOT NULL
                GROUP BY cm.original_column
                HAVING COUNT(DISTINCT cm.table_name) >= 2
                ORDER BY table_count DESC
                LIMIT 50
            """
            rows = self.handler.query(sql)
            
            for row in rows:
                col_name = row.get('original_column', '')
                
                # Check if column matches segmentation patterns
                col_lower = col_name.lower()
                for pattern, display_name in self.SEGMENTATION_PATTERNS:
                    if pattern in col_lower:
                        # Format display name
                        formatted_name = self._format_dimension_name(col_name, display_name)
                        dimensions.append((col_name, formatted_name))
                        break
            
        except Exception as e:
            logger.warning(f"[SCOPE] Could not discover segmentation dimensions: {e}")
            # Fallback: return empty, will skip scoping
        
        return dimensions[:10]  # Limit to top 10 candidates
    
    def _format_dimension_name(self, column_name: str, pattern_name: str) -> str:
        """Format a column name for display."""
        # Try to extract a nice name from the column
        name = column_name.replace('_code', '').replace('_', ' ').title()
        
        # Use pattern name if it's more descriptive
        if len(pattern_name) > len(name):
            return pattern_name
        
        return name
    
    def _query_segment_stats(self, dimension: str, dim_name: str, 
                            domain: str) -> List[ScopeSegment]:
        """Query actual statistics for a segmentation dimension.
        
        IMPORTANT: Counts DISTINCT employees (not rows) to avoid inflation
        when tables have multiple rows per employee (e.g., tax codes, deductions).
        """
        segments = []
        
        try:
            # Find tables with this dimension column
            tables_with_dim = self._find_tables_with_column(dimension)
            if not tables_with_dim:
                return segments
            
            # Find the best table (prefer employee/transaction tables)
            best_table = self._select_best_table(tables_with_dim, domain)
            if not best_table:
                return segments
            
            # Find employee identifier for DISTINCT counting
            emp_identifier = self._find_employee_identifier(best_table)
            
            # Build count expression - DISTINCT if we have an identifier, else COUNT(*)
            if emp_identifier:
                count_expr = f'COUNT(DISTINCT "{emp_identifier}")'
                logger.debug(f"[SCOPE] Using DISTINCT count on '{emp_identifier}' in '{best_table}'")
            else:
                count_expr = 'COUNT(*)'
                logger.debug(f"[SCOPE] No employee identifier found, using COUNT(*) for '{best_table}'")
            
            # Query distinct values with counts
            sql = f'''
                SELECT 
                    "{dimension}" as segment_value,
                    {count_expr} as employee_count
                FROM "{best_table}"
                WHERE "{dimension}" IS NOT NULL AND "{dimension}" != ''
                GROUP BY "{dimension}"
                ORDER BY employee_count DESC
                LIMIT 10
            '''
            
            rows = self.handler.query(sql)
            
            for row in rows:
                value = row.get('segment_value', '')
                count = row.get('employee_count', 0)
                
                if count >= self.MIN_SEGMENT_SIZE:
                    segments.append(ScopeSegment(
                        dimension=dimension,
                        value=str(value),
                        display_name=self._format_value(str(value), dim_name),
                        employee_count=count,
                        item_count=0,  # TODO: Query config count
                        unused_count=0,  # TODO: Calculate gaps
                        coverage_pct=0.0
                    ))
            
        except Exception as e:
            logger.error(f"[SCOPE] Error querying segments: {e}")
        
        return segments
    
    def _find_tables_with_column(self, column: str) -> List[str]:
        """Find all tables containing a specific column."""
        tables = []
        
        try:
            # Query _column_mappings - uses original_column, not column_name
            sql = f"""
                SELECT DISTINCT table_name 
                FROM _column_mappings 
                WHERE LOWER(original_column) = LOWER('{column}')
            """
            rows = self.handler.query(sql)
            tables = [r.get('table_name') for r in rows if r.get('table_name')]
        except Exception as e:
            logger.debug(f"[SCOPE] Could not query column mappings: {e}")
        
        return tables
    
    def _find_employee_identifier(self, table: str) -> Optional[str]:
        """Find the employee/person identifier column in a table for DISTINCT counting."""
        try:
            sql = f"""
                SELECT original_column 
                FROM _column_mappings 
                WHERE table_name = '{table}'
            """
            rows = self.handler.query(sql)
            
            for row in rows:
                col = row.get('original_column', '')
                if col.lower() in EMPLOYEE_IDENTIFIER_COLUMNS:
                    logger.debug(f"[SCOPE] Found employee identifier '{col}' in table '{table}'")
                    return col
                    
        except Exception as e:
            logger.debug(f"[SCOPE] Could not find employee identifier: {e}")
        
        return None
    
    def _select_best_table(self, tables: List[str], domain: str) -> Optional[str]:
        """Select the best table for querying (prefer transaction/employee tables)."""
        # Priority: employee tables > transaction tables > config tables
        for table in tables:
            t_lower = table.lower()
            if 'employee' in t_lower or 'worker' in t_lower:
                return table
        
        for table in tables:
            t_lower = table.lower()
            if 'transaction' in t_lower or 'payroll' in t_lower:
                return table
        
        # Return first available
        return tables[0] if tables else None
    
    def _format_value(self, value: str, dim_name: str) -> str:
        """Format a value for display."""
        # Common country code mappings
        if dim_name == 'Country':
            country_names = {
                'US': 'United States',
                'USA': 'United States',
                'CAN': 'Canada',
                'CA': 'Canada',
                'UK': 'United Kingdom',
                'GB': 'United Kingdom',
                'MX': 'Mexico',
            }
            return country_names.get(value.upper(), value)
        
        return value
    
    def _should_ask_clarification(self, segments: List[ScopeSegment]) -> bool:
        """Determine if we should ask a clarifying question."""
        if len(segments) < self.MIN_SEGMENTS_TO_ASK:
            return False
        
        # Count segments with actual employees
        segments_with_employees = [s for s in segments if s.employee_count > 0]
        
        # If 2+ segments have employees, ALWAYS ask
        if len(segments_with_employees) >= 2:
            return True
        
        return False
    
    def _build_clarifying_question(self, domain: str, segments: List[ScopeSegment]) -> str:
        """Build an intelligent clarifying question."""
        if not segments:
            return ""
        
        dim_name = segments[0].dimension.replace('_code', '').replace('_', ' ').title()
        total_employees = sum(s.employee_count for s in segments)
        
        # Build the question with actual data
        lines = [
            f"Your {domain} data spans {len(segments)} {dim_name.lower()}s with active usage:",
            ""
        ]
        
        for seg in segments:
            # Show actual employee counts
            unused_note = f" ⚠️ {seg.unused_count} unused" if seg.unused_count > 0 else ""
            lines.append(f"**{seg.display_name}** ({seg.employee_count:,} employees){unused_note}")
            if seg.item_count > 0:
                lines.append(f"  • {seg.item_count} {domain} codes in use")
        
        lines.extend([
            "",
            "Which should I focus on? Or pull everything?"
        ])
        
        return "\n".join(lines)
    
    def get_scope_summary(self, analysis: ScopeAnalysis) -> str:
        """Get a summary string for logging/display."""
        if analysis.needs_clarification:
            return f"Need clarification: {len(analysis.segments)} segments found"
        else:
            return f"Proceeding: {analysis.total_employees:,} employees, {analysis.total_items} items"


def analyze_question_scope(project_name: str, question: str, 
                          handler=None, context: Dict = None) -> ScopeAnalysis:
    """
    Convenience function to analyze question scope.
    
    Args:
        project_name: Project code
        question: User's question
        handler: DuckDB handler
        context: Additional context
        
    Returns:
        ScopeAnalysis with scoping recommendation
    """
    scoper = IntelligentScoping(project_name, handler)
    return scoper.analyze(question, context)
