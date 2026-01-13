"""
XLR8 Intelligence Engine - Consultative Response Templates
============================================================
VERSION: 1.0.0

Generate professional consultative responses without LLM calls.
Used by deterministic path when synthesis pipeline isn't available
or for fast template-based responses.

These templates transform raw data results into consultant-quality
responses that provide context, insights, and next steps.

Deploy to: backend/utils/intelligence/consultative_templates.py
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def format_count_response(
    count: int,
    entity: str,
    table_name: str,
    filters: List[Dict] = None,
    project: str = None,
    sql: str = None
) -> str:
    """
    Generate consultative count response.
    
    Transforms "Found 14474 records" into a professional response
    with context, meaning, and actionable next steps.
    
    Args:
        count: Number of records found
        entity: What we're counting (employees, deductions, etc.)
        table_name: Source table name
        filters: Applied filters [{column, operator, value}, ...]
        project: Project name for context
        sql: Executed SQL for transparency
        
    Returns:
        Consultative response string
    """
    # Normalize entity name
    entity_display = _humanize_entity(entity)
    
    # Build filter description
    filter_desc = _describe_filters(filters) if filters else ""
    
    # Start building response
    parts = []
    
    # Lead with the answer
    if count == 0:
        parts.append(f"**No {entity_display}** found{filter_desc}.")
        parts.append("")
        parts.append("### What This Means")
        parts.append("No records match your criteria. This could indicate:")
        parts.append("- The data hasn't been uploaded yet")
        parts.append("- Filter criteria may be too restrictive")
        parts.append("- Different terminology might be used in your source system")
        parts.append("")
        parts.append("### Recommended Actions")
        parts.append("- Verify the data has been uploaded for this project")
        parts.append("- Try broadening your search criteria")
        parts.append("- Check if the data uses different field names or codes")
    elif count == 1:
        parts.append(f"**1 {entity_display[:-1] if entity_display.endswith('s') else entity_display}** found{filter_desc}.")
        parts.append("")
        parts.append("### Details")
        parts.append("A single record matches your criteria. This might be exactly what you're looking for, or it could indicate incomplete data.")
    else:
        # Format with thousands separator
        count_formatted = f"{count:,}"
        parts.append(f"**{count_formatted} {entity_display}** found{filter_desc}.")
        parts.append("")
        
        # Add contextual meaning based on count
        parts.append("### What This Means")
        if count < 10:
            parts.append(f"This is a small subset ({count} records). Consider reviewing each record individually for accuracy.")
        elif count < 100:
            parts.append(f"This represents a manageable dataset of {count_formatted} records that can be reviewed in detail.")
        elif count < 1000:
            parts.append(f"This is a moderate dataset. Consider grouping by department, location, or status for easier analysis.")
        elif count < 10000:
            parts.append(f"This is a substantial dataset of {count_formatted} records. Breaking down by key dimensions will help identify patterns.")
        else:
            parts.append(f"This is a large population of {count_formatted} records. Focus on aggregations and breakdowns rather than individual review.")
        
        parts.append("")
        parts.append("### Recommended Next Steps")
        parts.append(f"- **Break down by dimension**: Ask \"How many {entity_display} by department?\" or \"...by location?\"")
        parts.append(f"- **Filter further**: Add criteria like status, date range, or specific codes")
        parts.append(f"- **Export for analysis**: Request an Excel export for detailed offline review")
        if entity_display.lower() in ['employees', 'workers', 'staff']:
            parts.append(f"- **Compare to benchmarks**: Check against your expected headcount or prior period")
    
    # Add source attribution
    parts.append("")
    parts.append("---")
    source_name = _humanize_table_name(table_name)
    parts.append(f"*Source: {source_name}*")
    
    return "\n".join(parts)


def format_aggregation_response(
    agg_type: str,
    value: Any,
    column: str,
    table_name: str,
    filters: List[Dict] = None,
    row_count: int = None
) -> str:
    """
    Generate consultative aggregation response (sum, avg, min, max).
    
    Args:
        agg_type: Type of aggregation (sum, average, minimum, maximum)
        value: Calculated value
        column: Column that was aggregated
        table_name: Source table
        filters: Applied filters
        row_count: Number of records in aggregation
        
    Returns:
        Consultative response string
    """
    # Determine display label
    agg_labels = {
        'sum': 'Total',
        'total': 'Total',
        'average': 'Average',
        'avg': 'Average',
        'mean': 'Average',
        'minimum': 'Minimum',
        'min': 'Minimum',
        'maximum': 'Maximum',
        'max': 'Maximum'
    }
    label = agg_labels.get(agg_type.lower(), 'Result')
    
    # Format value appropriately
    formatted_value = _format_value(value, column)
    
    # Humanize column name
    column_display = _humanize_column(column)
    
    # Build filter description
    filter_desc = _describe_filters(filters) if filters else ""
    
    parts = []
    
    # Lead with the answer
    parts.append(f"**{label}: {formatted_value}**")
    if filter_desc:
        parts.append(f"*{filter_desc.strip()}*")
    parts.append("")
    
    # Add context
    parts.append("### Calculation Details")
    parts.append(f"- **Metric**: {label} of {column_display}")
    parts.append(f"- **Source**: {_humanize_table_name(table_name)}")
    if row_count:
        parts.append(f"- **Records included**: {row_count:,}")
    
    # Add interpretive guidance based on aggregation type
    parts.append("")
    parts.append("### Considerations")
    
    if agg_type.lower() in ['sum', 'total']:
        parts.append("- This total represents the complete sum across all matching records")
        parts.append("- Consider breaking down by category to understand composition")
        parts.append("- Compare against budget or prior period for variance analysis")
    elif agg_type.lower() in ['average', 'avg', 'mean']:
        parts.append("- This average may be affected by outliers - consider also checking min/max")
        parts.append("- Compare against industry benchmarks if available")
        parts.append("- Breaking down by group can reveal if some segments skew the average")
    elif agg_type.lower() in ['minimum', 'min']:
        parts.append("- This represents the lowest value in your dataset")
        parts.append("- Consider whether this minimum is expected or indicates a data quality issue")
        parts.append("- Investigate which specific record(s) have this minimum value")
    elif agg_type.lower() in ['maximum', 'max']:
        parts.append("- This represents the highest value in your dataset")
        parts.append("- Consider whether this maximum is expected or an outlier")
        parts.append("- May warrant review if significantly higher than typical values")
    
    parts.append("")
    parts.append("### Recommended Next Steps")
    parts.append(f"- Compare this {label.lower()} against your expectations or benchmarks")
    parts.append(f"- Break down by dimension to understand what's driving this number")
    parts.append(f"- Export the underlying data for detailed analysis")
    
    return "\n".join(parts)


def format_group_by_response(
    rows: List[Dict],
    dimension_column: str,
    value_column: str,
    agg_type: str = 'count',
    table_name: str = None,
    filters: List[Dict] = None,
    total: int = None
) -> str:
    """
    Generate consultative response for GROUP BY queries.
    
    Args:
        rows: Result rows [{dimension: value, metric: value}, ...]
        dimension_column: Column used for grouping
        value_column: Column with aggregated values
        agg_type: Type of aggregation
        table_name: Source table
        filters: Applied filters
        total: Total across all groups
        
    Returns:
        Consultative response string
    """
    dimension_display = _humanize_column(dimension_column)
    filter_desc = _describe_filters(filters) if filters else ""
    
    parts = []
    
    # Calculate total if not provided
    if total is None:
        total = sum(r.get(value_column, 0) for r in rows if isinstance(r.get(value_column), (int, float)))
    
    # Lead with summary
    parts.append(f"**Breakdown by {dimension_display}**{filter_desc}")
    parts.append(f"*{len(rows)} groups, {total:,} total*")
    parts.append("")
    
    # Show the breakdown (limit to top 20)
    display_rows = rows[:20]
    
    # Find max value for percentage calculations
    max_val = max((r.get(value_column, 0) for r in rows if isinstance(r.get(value_column), (int, float))), default=1)
    
    for row in display_rows:
        dim_val = row.get(dimension_column, 'Unknown') or 'Not Specified'
        metric_val = row.get(value_column, 0)
        
        # Format the metric value
        if isinstance(metric_val, float):
            metric_formatted = f"{metric_val:,.2f}"
        elif isinstance(metric_val, int):
            metric_formatted = f"{metric_val:,}"
        else:
            metric_formatted = str(metric_val)
        
        # Calculate percentage of total if numeric
        if isinstance(metric_val, (int, float)) and total > 0:
            pct = (metric_val / total) * 100
            parts.append(f"- **{dim_val}**: {metric_formatted} ({pct:.1f}%)")
        else:
            parts.append(f"- **{dim_val}**: {metric_formatted}")
    
    if len(rows) > 20:
        parts.append(f"- *...and {len(rows) - 20} more groups*")
    
    # Add insights
    parts.append("")
    parts.append("### Key Observations")
    
    if len(rows) > 0:
        # Find top and bottom
        sorted_rows = sorted(rows, key=lambda r: r.get(value_column, 0) if isinstance(r.get(value_column), (int, float)) else 0, reverse=True)
        top = sorted_rows[0]
        bottom = sorted_rows[-1] if len(sorted_rows) > 1 else None
        
        top_val = top.get(value_column, 0)
        top_dim = top.get(dimension_column, 'Unknown')
        if isinstance(top_val, (int, float)) and total > 0:
            top_pct = (top_val / total) * 100
            parts.append(f"- **Largest**: {top_dim} accounts for {top_pct:.1f}% of the total")
        
        if bottom and len(sorted_rows) > 2:
            bottom_val = bottom.get(value_column, 0)
            bottom_dim = bottom.get(dimension_column, 'Unknown')
            parts.append(f"- **Smallest**: {bottom_dim} with {_format_value(bottom_val, value_column)}")
        
        # Check for concentration
        if len(sorted_rows) >= 3:
            top_3_total = sum(r.get(value_column, 0) for r in sorted_rows[:3] if isinstance(r.get(value_column), (int, float)))
            if total > 0:
                concentration = (top_3_total / total) * 100
                if concentration > 70:
                    parts.append(f"- **Concentration**: Top 3 {dimension_display}s represent {concentration:.0f}% of total")
    
    parts.append("")
    parts.append("### Recommended Next Steps")
    parts.append(f"- Drill into specific {dimension_display}s for more detail")
    parts.append("- Compare against prior periods to identify trends")
    parts.append("- Export this breakdown for reporting or further analysis")
    
    # Source attribution
    if table_name:
        parts.append("")
        parts.append("---")
        parts.append(f"*Source: {_humanize_table_name(table_name)}*")
    
    return "\n".join(parts)


def format_list_response(
    rows: List[Dict],
    columns: List[str],
    table_name: str,
    total_count: int = None,
    filters: List[Dict] = None,
    entity: str = "records"
) -> str:
    """
    Generate consultative response for LIST queries.
    
    Args:
        rows: Data rows (limited preview)
        columns: Column names
        table_name: Source table
        total_count: Total matching records (may exceed len(rows))
        filters: Applied filters
        entity: What we're listing
        
    Returns:
        Consultative response string
    """
    total = total_count or len(rows)
    showing = min(len(rows), 10)
    filter_desc = _describe_filters(filters) if filters else ""
    entity_display = _humanize_entity(entity)
    
    parts = []
    
    # Summary
    parts.append(f"**{total:,} {entity_display}** found{filter_desc}")
    if total > showing:
        parts.append(f"*Showing first {showing} of {total:,}*")
    parts.append("")
    
    # Show preview of data
    if rows and columns:
        # Pick key columns to display (first 4-5 meaningful ones)
        display_cols = _select_display_columns(columns)[:5]
        
        parts.append("### Preview")
        for i, row in enumerate(rows[:10], 1):
            row_parts = []
            for col in display_cols:
                val = row.get(col, '')
                if val is not None and val != '':
                    col_label = _humanize_column(col)
                    row_parts.append(f"{col_label}: {val}")
            if row_parts:
                parts.append(f"{i}. {' | '.join(row_parts[:3])}")
        
        if total > 10:
            parts.append(f"*...and {total - 10:,} more*")
    
    parts.append("")
    parts.append("### Next Steps")
    parts.append("- Add filters to narrow your results")
    parts.append("- Request a specific count or aggregation")
    parts.append("- Export to Excel for full dataset access")
    
    # Source
    parts.append("")
    parts.append("---")
    parts.append(f"*Source: {_humanize_table_name(table_name)}*")
    
    return "\n".join(parts)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _humanize_entity(entity: str) -> str:
    """Convert entity code to human-readable plural form."""
    entity_map = {
        'employee': 'employees',
        'employees': 'employees',
        'hr': 'employees',
        'deduction': 'deductions',
        'earning': 'earnings',
        'tax': 'tax records',
        'benefit': 'benefit records',
        'config': 'configuration records',
        'record': 'records',
    }
    return entity_map.get(entity.lower(), f"{entity}s" if not entity.endswith('s') else entity)


def _humanize_table_name(table_name: str) -> str:
    """Convert table name to human-readable form."""
    if not table_name:
        return "Data Source"
    
    # Remove project prefix (everything before __)
    if '__' in table_name:
        table_name = table_name.split('__')[-1]
    
    # Convert underscores to spaces and title case
    return table_name.replace('_', ' ').title()


def _humanize_column(column: str) -> str:
    """Convert column name to human-readable form."""
    if not column:
        return "Value"
    
    # Handle common abbreviations
    abbrevs = {
        'emp': 'Employee',
        'dept': 'Department',
        'loc': 'Location',
        'amt': 'Amount',
        'qty': 'Quantity',
        'num': 'Number',
        'dt': 'Date',
        'cd': 'Code',
        'desc': 'Description',
        'id': 'ID',
        'ssn': 'SSN',
    }
    
    # Replace underscores, handle abbreviations, title case
    words = column.lower().replace('_', ' ').split()
    result = []
    for word in words:
        result.append(abbrevs.get(word, word.title()))
    
    return ' '.join(result)


def _describe_filters(filters: List[Dict]) -> str:
    """Create human-readable filter description."""
    if not filters:
        return ""
    
    # Limit to 3 filters for readability
    descriptions = []
    for f in filters[:3]:
        col = _humanize_column(f.get('column', ''))
        val = f.get('value', f.get('match_value', ''))
        op = f.get('operator', '=')
        
        if op in ['=', '==', 'IS']:
            descriptions.append(f"{col} = \"{val}\"")
        elif op in ['!=', '<>', 'IS NOT']:
            descriptions.append(f"{col} ≠ \"{val}\"")
        elif op in ['>', '>=', '<', '<=']:
            descriptions.append(f"{col} {op} {val}")
        elif op == 'LIKE':
            descriptions.append(f"{col} contains \"{val}\"")
        elif op == 'IN':
            descriptions.append(f"{col} in [{val}]")
        else:
            descriptions.append(f"{col} {op} {val}")
    
    if len(filters) > 3:
        descriptions.append(f"+{len(filters) - 3} more filters")
    
    return " where " + ", ".join(descriptions) if descriptions else ""


def _format_value(value: Any, column: str = '') -> str:
    """Format a value appropriately based on type and context."""
    if value is None:
        return "N/A"
    
    # Check if it looks like currency
    is_currency = any(term in column.lower() for term in ['salary', 'pay', 'amount', 'rate', 'wage', 'cost', 'price', 'total', 'sum'])
    
    if isinstance(value, float):
        if is_currency:
            return f"${value:,.2f}"
        elif abs(value) < 1:
            return f"{value:.4f}"
        else:
            return f"{value:,.2f}"
    elif isinstance(value, int):
        if is_currency and value > 100:
            return f"${value:,}"
        return f"{value:,}"
    else:
        return str(value)


def _select_display_columns(columns: List[str]) -> List[str]:
    """Select the most meaningful columns to display."""
    if not columns:
        return []
    
    # Priority columns (things users care about)
    priority_patterns = [
        'name', 'employee', 'description', 'desc', 'title',
        'code', 'id', 'number', 'status', 'type',
        'department', 'location', 'company'
    ]
    
    # Skip boring columns
    skip_patterns = ['created', 'updated', 'modified', 'timestamp', 'uuid', 'hash']
    
    priority = []
    regular = []
    
    for col in columns:
        col_lower = col.lower()
        
        # Skip boring columns
        if any(skip in col_lower for skip in skip_patterns):
            continue
        
        # Prioritize interesting columns
        if any(prio in col_lower for prio in priority_patterns):
            priority.append(col)
        else:
            regular.append(col)
    
    return priority + regular
