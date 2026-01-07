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
    """
    
    # Domain keywords to hub mappings
    DOMAIN_HUBS = {
        'deduction': ['deductionbenefit_code', 'deduction_code', 'benefit_code'],
        'earning': ['earnings_code', 'earning_code'],
        'tax': ['tax_code', 'tax_type'],
        'employee': ['employee_number', 'emp_id'],
        'company': ['company_code', 'home_company_code'],
        'pay': ['pay_group_code', 'pay_frequency_code'],
        'job': ['job_code', 'position_code'],
        'location': ['location_code', 'work_location_code'],
        'org': ['org_level_1_code', 'org_level_2_code', 'org_level_3_code'],
        'project': ['project_code'],
    }
    
    # Primary segmentation dimensions (in priority order)
    SEGMENTATION_DIMS = [
        ('country_code', 'Country'),
        ('home_company_code', 'Company'),
        ('company_code', 'Company'),
        ('org_level_1_code', 'Division'),
        ('pay_group_code', 'Pay Group'),
    ]
    
    # Thresholds
    MIN_SEGMENT_SIZE = 10          # Minimum employees to be a meaningful segment
    MIN_SEGMENTS_TO_ASK = 2        # Need at least 2 segments to ask clarification
    MAX_SEGMENTS_TO_SHOW = 5       # Don't overwhelm with too many options
    
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
        """Detect the domain of the question."""
        q_lower = question.lower()
        
        # Check each domain's keywords
        for domain, keywords in [
            ('deduction', ['deduction', 'benefit', 'garnish', '401k', 'insurance']),
            ('earning', ['earning', 'wage', 'salary', 'bonus', 'overtime', 'pay code']),
            ('tax', ['tax', 'withhold', 'sui', 'sdi', 'fica', 'w2', 'w4']),
            ('employee', ['employee', 'worker', 'staff', 'headcount', 'roster']),
            ('company', ['company', 'entity', 'legal entity']),
            ('pay', ['pay group', 'pay frequency', 'payroll', 'pay period']),
            ('job', ['job', 'position', 'title', 'role']),
            ('location', ['location', 'site', 'work location', 'office']),
            ('org', ['org level', 'department', 'division', 'cost center']),
            ('project', ['project', 'project code']),
        ]:
            if any(kw in q_lower for kw in keywords):
                return domain
        
        return 'general'
    
    def _get_relevant_hubs(self, domain: str, context: Dict = None) -> List[str]:
        """Get hub columns relevant to this domain."""
        hubs = self.DOMAIN_HUBS.get(domain, [])
        
        # Always include segmentation dimensions
        hubs.extend([dim for dim, _ in self.SEGMENTATION_DIMS])
        
        return list(set(hubs))
    
    def _analyze_segments(self, domain: str, relevant_hubs: List[str], 
                         context: Dict = None) -> List[ScopeSegment]:
        """Analyze data segments based on primary dimensions."""
        segments = []
        
        if not self.handler:
            logger.warning("[SCOPE] No handler available for segment analysis")
            return segments
        
        # Try each segmentation dimension
        for dim_column, dim_name in self.SEGMENTATION_DIMS:
            dim_segments = self._query_segment_stats(dim_column, dim_name, domain)
            if dim_segments and len(dim_segments) >= self.MIN_SEGMENTS_TO_ASK:
                # Found meaningful segmentation
                segments = dim_segments[:self.MAX_SEGMENTS_TO_SHOW]
                break
        
        return segments
    
    def _query_segment_stats(self, dimension: str, dim_name: str, 
                            domain: str) -> List[ScopeSegment]:
        """Query actual statistics for a segmentation dimension."""
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
            
            # Query distinct values with counts
            sql = f'''
                SELECT 
                    "{dimension}" as segment_value,
                    COUNT(*) as record_count
                FROM "{best_table}"
                WHERE "{dimension}" IS NOT NULL AND "{dimension}" != ''
                GROUP BY "{dimension}"
                ORDER BY record_count DESC
                LIMIT 10
            '''
            
            rows = self.handler.query(sql)
            
            for row in rows:
                value = row.get('segment_value', '')
                count = row.get('record_count', 0)
                
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
            # Query _column_mappings or information_schema
            sql = f"""
                SELECT DISTINCT table_name 
                FROM _column_mappings 
                WHERE LOWER(column_name) = LOWER('{column}')
            """
            rows = self.handler.query(sql)
            tables = [r.get('table_name') for r in rows if r.get('table_name')]
        except Exception as e:
            logger.debug(f"[SCOPE] Could not query column mappings: {e}")
        
        return tables
    
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
        
        # Check if segments are meaningfully different in size
        if segments:
            total = sum(s.employee_count for s in segments)
            largest = max(s.employee_count for s in segments)
            
            # If one segment dominates (>80%), don't ask
            if largest > total * 0.8:
                return False
            
            # If we have meaningful distribution, ask
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
