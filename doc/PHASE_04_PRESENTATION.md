# Phase 4: Presentation

**Status:** NOT STARTED  
**Total Estimated Hours:** 10-12  
**Dependencies:** Phase 3 (Synthesis) substantially complete  
**Last Updated:** January 11, 2026

---

## Objective

Make it look professional. The engine can find the right data and synthesize insights - now we need to present those insights in a way that impresses clients and passes due diligence.

---

## Background

### Current State

Current presentation:
- Basic markdown formatting
- Inconsistent styling
- No error handling for edge cases
- Generic layouts

### Target State

Professional presentation:
- Polished chat responses
- Consistent styling
- Graceful degradation on errors
- Export-ready formatting

---

## Component Overview

| # | Component | Hours | Description |
|---|-----------|-------|-------------|
| 4.1 | Chat Response Styling | 3-4 | Beautiful, consistent chat messages |
| 4.2 | Response Structure Polish | 2-3 | Logical flow, scannable layout |
| 4.3 | Export Formatting | 3-4 | PDF/Excel export quality |
| 4.4 | Error Handling & Edge Cases | 2-3 | Graceful failures |

---

## Component 4.1: Chat Response Styling

**Goal:** Chat responses that look like they came from a premium product.

### Typography

```css
/* Response container */
.response-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 15px;
    line-height: 1.6;
    color: #1a1a1a;
}

/* Headers - consultative style */
.response-container h3 {
    font-size: 16px;
    font-weight: 600;
    color: #0d47a1;
    margin-top: 16px;
    margin-bottom: 8px;
}

/* Numbers - prominent */
.stat-number {
    font-size: 24px;
    font-weight: 700;
    color: #1565c0;
}

/* Data tables */
.data-table {
    font-size: 13px;
    border-collapse: collapse;
    margin: 12px 0;
}

.data-table th {
    background: #f5f7fa;
    font-weight: 600;
    text-align: left;
    padding: 8px 12px;
    border-bottom: 2px solid #e0e0e0;
}

.data-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #eee;
}
```

### Response Components

```jsx
// Stat highlight - for key numbers
const StatHighlight = ({ value, label, trend }) => (
    <div className="stat-highlight">
        <div className="stat-number">{value.toLocaleString()}</div>
        <div className="stat-label">{label}</div>
        {trend && <TrendIndicator trend={trend} />}
    </div>
);

// Data preview - for sample rows
const DataPreview = ({ columns, rows, totalCount }) => (
    <div className="data-preview">
        <table className="data-table">
            <thead>
                <tr>{columns.map(c => <th key={c}>{formatHeader(c)}</th>)}</tr>
            </thead>
            <tbody>
                {rows.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                        {columns.map(c => <td key={c}>{row[c]}</td>)}
                    </tr>
                ))}
            </tbody>
        </table>
        {totalCount > 5 && (
            <div className="more-rows">
                + {totalCount - 5} more rows
            </div>
        )}
    </div>
);

// Gap alert - for detected issues
const GapAlert = ({ gap }) => (
    <div className={`gap-alert severity-${gap.severity.toLowerCase()}`}>
        <div className="gap-icon">{getSeverityIcon(gap.severity)}</div>
        <div className="gap-content">
            <div className="gap-title">{gap.title}</div>
            <div className="gap-description">{gap.description}</div>
            {gap.recommendation && (
                <div className="gap-action">{gap.recommendation}</div>
            )}
        </div>
    </div>
);

// Citation footer
const CitationFooter = ({ citations }) => (
    <div className="citations">
        <div className="citations-header">Sources</div>
        {citations.map((c, i) => (
            <span key={i} className="citation">
                [{i + 1}] {c.source_document}
                {c.page_number && `, p.${c.page_number}`}
            </span>
        ))}
    </div>
);
```

### Response Type Templates

```jsx
// COUNT response
const CountResponse = ({ result }) => (
    <div className="response count-response">
        <StatHighlight 
            value={result.count} 
            label={result.entity}
        />
        {result.breakdown && (
            <div className="breakdown">
                <h4>Breakdown</h4>
                <BreakdownChart data={result.breakdown} />
            </div>
        )}
        {result.gaps.length > 0 && (
            <div className="gaps-section">
                {result.gaps.map(g => <GapAlert key={g.id} gap={g} />)}
            </div>
        )}
        {result.citations.length > 0 && (
            <CitationFooter citations={result.citations} />
        )}
    </div>
);

// LIST response
const ListResponse = ({ result }) => (
    <div className="response list-response">
        <div className="summary">
            Found <strong>{result.count.toLocaleString()}</strong> {result.entity}
        </div>
        <DataPreview 
            columns={result.columns}
            rows={result.data}
            totalCount={result.count}
        />
        {result.insights && (
            <div className="insights">{result.insights}</div>
        )}
        {result.citations.length > 0 && (
            <CitationFooter citations={result.citations} />
        )}
    </div>
);

// GAP ANALYSIS response
const GapAnalysisResponse = ({ result }) => (
    <div className="response gap-analysis-response">
        <h3>Gap Analysis: {result.topic}</h3>
        <TruthStatusTable truths={result.truthStatus} />
        <div className="gaps-section">
            {result.gaps.map(g => <GapAlert key={g.id} gap={g} />)}
        </div>
        <div className="recommendations">
            <h4>Recommended Actions</h4>
            <ol>
                {result.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                ))}
            </ol>
        </div>
    </div>
);
```

---

## Component 4.2: Response Structure Polish

**Goal:** Responses that are easy to scan and understand.

### Information Hierarchy

```
1. HEADLINE (What's the answer?)
   - Big number or direct statement
   - Immediately answers the question
   
2. CONTEXT (Why does it matter?)
   - Supporting details
   - Comparison to benchmarks
   - Trend if relevant
   
3. DETAIL (What's the data?)
   - Table or chart
   - Sample rows
   - Breakdown by dimension
   
4. ALERTS (What needs attention?)
   - Gaps detected
   - Recommendations
   - Compliance notes
   
5. SOURCES (Where did this come from?)
   - Citation links
   - Data freshness
```

### Scannable Formatting Rules

```python
FORMATTING_RULES = {
    # Numbers
    'format_numbers': {
        'thousands': True,           # 1,234 not 1234
        'decimals': 2,               # For money
        'percentages': 1,            # For rates
        'currency_symbol': True,     # $1,234.00
    },
    
    # Headers
    'use_headers': {
        'min_sections': 2,           # Use headers if 2+ sections
        'max_header_length': 40,     # Keep them short
        'header_level': 3,           # h3 for sections
    },
    
    # Lists
    'use_lists': {
        'min_items': 3,              # Use list if 3+ items
        'max_items': 7,              # Collapse if >7
        'bullet_style': '•',         # Consistent bullets
    },
    
    # Tables
    'use_tables': {
        'min_rows': 2,               # Table if 2+ rows
        'max_display_rows': 10,      # Truncate with "more"
        'max_columns': 6,            # Horizontal scroll if >6
        'align_numbers': 'right',    # Numbers right-aligned
    },
    
    # Emphasis
    'bold': {
        'key_numbers': True,         # Bold important stats
        'entity_names': True,        # Bold proper nouns
        'max_per_paragraph': 2,      # Don't overuse
    }
}
```

### Response Flow Templates

```python
# COUNT query flow
COUNT_FLOW = """
## {count:,} {entity}

{context_sentence}

{breakdown_table_if_relevant}

{gaps_if_any}

{citations}
"""

# LIST query flow
LIST_FLOW = """
Found **{count:,} {entity}** matching your query.

{data_table}

{insights_if_any}

{next_steps_if_relevant}
"""

# COMPARE query flow
COMPARE_FLOW = """
## {comparison_title}

{comparison_chart}

### Key Differences
{differences_list}

### Recommendation
{recommendation}
"""
```

---

## Component 4.3: Export Formatting

**Goal:** Exports that are ready for client presentations.

### PDF Export

```python
class PDFExporter:
    """Generate professional PDF reports."""
    
    def __init__(self):
        self.styles = {
            'title': {
                'font': 'Helvetica-Bold',
                'size': 24,
                'color': '#0d47a1'
            },
            'heading': {
                'font': 'Helvetica-Bold',
                'size': 14,
                'color': '#333333'
            },
            'body': {
                'font': 'Helvetica',
                'size': 11,
                'color': '#333333',
                'line_height': 1.4
            },
            'table_header': {
                'font': 'Helvetica-Bold',
                'size': 10,
                'background': '#f5f7fa'
            }
        }
    
    def export_response(self, response: SynthesisResult) -> bytes:
        """Export a synthesis response to PDF."""
        doc = Document()
        
        # Header with logo space
        doc.add_header(
            title=f"Analysis: {response.query}",
            date=datetime.now(),
            project=response.project
        )
        
        # Executive summary
        doc.add_section("Summary", response.response[:500])
        
        # Data table if present
        if response.data:
            doc.add_table(
                headers=response.columns,
                rows=response.data[:20],
                title="Data Sample"
            )
        
        # Gaps section
        if response.gaps:
            doc.add_section("Identified Gaps")
            for gap in response.gaps:
                doc.add_gap_alert(gap)
        
        # Citations
        if response.citations:
            doc.add_citations(response.citations)
        
        # Footer
        doc.add_footer(
            text="Generated by XLR8 Analysis Platform",
            page_numbers=True
        )
        
        return doc.render()
```

### Excel Export

```python
class ExcelExporter:
    """Generate professional Excel workbooks."""
    
    def export_data(self, 
                   data: List[Dict], 
                   metadata: Dict) -> bytes:
        """Export data with formatting."""
        wb = Workbook()
        
        # Summary sheet
        summary = wb.create_sheet("Summary")
        summary.add_header(metadata['query'])
        summary.add_stat_row("Total Records", len(data))
        summary.add_stat_row("Generated", datetime.now())
        
        # Data sheet
        data_sheet = wb.create_sheet("Data")
        data_sheet.write_headers(data[0].keys())
        for row in data:
            data_sheet.write_row(row.values())
        
        # Apply formatting
        data_sheet.format_as_table()
        data_sheet.auto_column_widths()
        data_sheet.freeze_header_row()
        
        # Gap analysis sheet if relevant
        if metadata.get('gaps'):
            gaps_sheet = wb.create_sheet("Gap Analysis")
            gaps_sheet.write_gaps(metadata['gaps'])
        
        return wb.save()
```

### Export Button Integration

```jsx
const ExportMenu = ({ response }) => {
    const [exporting, setExporting] = useState(false);
    
    const handleExport = async (format) => {
        setExporting(true);
        try {
            const blob = await api.exportResponse(response.id, format);
            downloadBlob(blob, `analysis-${response.id}.${format}`);
        } finally {
            setExporting(false);
        }
    };
    
    return (
        <Dropdown label="Export" disabled={exporting}>
            <DropdownItem onClick={() => handleExport('pdf')}>
                PDF Report
            </DropdownItem>
            <DropdownItem onClick={() => handleExport('xlsx')}>
                Excel Workbook
            </DropdownItem>
            <DropdownItem onClick={() => handleExport('csv')}>
                CSV Data
            </DropdownItem>
        </Dropdown>
    );
};
```

---

## Component 4.4: Error Handling & Edge Cases

**Goal:** Graceful degradation when things go wrong.

### Error Types and Responses

```python
ERROR_RESPONSES = {
    'no_data': {
        'message': "No data found matching your query.",
        'suggestion': "Try broadening your search criteria.",
        'show_alternatives': True
    },
    
    'ambiguous_query': {
        'message': "I'm not sure what you're looking for.",
        'suggestion': "Could you be more specific?",
        'show_examples': True
    },
    
    'missing_table': {
        'message': "The required data hasn't been uploaded yet.",
        'suggestion': "Upload the {table_type} data to answer this question.",
        'show_upload_link': True
    },
    
    'query_timeout': {
        'message': "This query is taking longer than expected.",
        'suggestion': "Try narrowing your search or filtering by date.",
        'show_retry': True
    },
    
    'llm_error': {
        'message': "I couldn't generate a complete response.",
        'suggestion': "Here's what I found in the data:",
        'show_raw_data': True
    }
}
```

### Graceful Degradation

```python
class ResponseBuilder:
    """Build response with graceful degradation."""
    
    def build(self, synthesis_result: SynthesisResult) -> Response:
        """
        Build response, falling back gracefully on errors.
        """
        try:
            # Try full synthesis response
            return self._build_full_response(synthesis_result)
        except SynthesisError:
            # Fall back to data-only response
            return self._build_data_response(synthesis_result)
        except DataError:
            # Fall back to explanation
            return self._build_explanation_response(synthesis_result)
        except Exception as e:
            # Last resort - helpful error
            return self._build_error_response(e)
    
    def _build_data_response(self, result: SynthesisResult) -> Response:
        """Show just the data when synthesis fails."""
        return Response(
            type='data_only',
            header="Here's what I found:",
            data=result.sql_results.data,
            note="I couldn't generate a full analysis, but here's the raw data."
        )
    
    def _build_explanation_response(self, result: SynthesisResult) -> Response:
        """Explain what we tried when data fails."""
        return Response(
            type='explanation',
            header="Let me explain what I looked for:",
            explanation=f"I searched for {result.query} "
                       f"in the {result.domain} data.",
            suggestion="This data may not have been uploaded yet."
        )
```

### Edge Case Handling

```python
EDGE_CASES = {
    # Single result
    'single_row': {
        'handler': 'format_single_result',
        'template': "Found 1 {entity}: {summary}"
    },
    
    # Empty result
    'no_rows': {
        'handler': 'format_empty_result',
        'template': "No {entity} found matching these criteria."
    },
    
    # Very large result
    'large_result': {
        'threshold': 10000,
        'handler': 'format_large_result',
        'template': "Found {count:,} {entity}. Showing summary..."
    },
    
    # All null column
    'null_column': {
        'handler': 'format_null_column',
        'note': "Note: {column} has no values in this dataset."
    },
    
    # Mixed types
    'mixed_types': {
        'handler': 'format_mixed_types',
        'note': "Note: {column} contains mixed data types."
    }
}

def handle_edge_case(case_type: str, context: Dict) -> str:
    """Generate appropriate response for edge case."""
    config = EDGE_CASES.get(case_type, {})
    template = config.get('template', 'Unexpected result.')
    return template.format(**context)
```

---

## Testing Strategy

### Visual Testing
- Screenshot comparisons for styling
- Cross-browser rendering checks
- Mobile responsiveness

### Export Testing
- PDF renders correctly
- Excel formulas work
- CSV encoding is correct

### Edge Case Testing
- Empty results
- Single results
- Very large results
- Error conditions

---

## Success Criteria

### Phase Complete When:
1. Chat responses styled consistently
2. Response structure scannable and logical
3. PDF and Excel exports professional quality
4. All error cases handled gracefully

### Quality Gates:
- Zero broken layouts
- Exports open correctly in target apps
- Error messages are helpful, not cryptic
- Mobile view works properly

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-11 | Initial detailed phase doc created |
