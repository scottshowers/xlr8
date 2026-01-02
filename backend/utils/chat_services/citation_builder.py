"""
Citation Builder
================

Every claim backed by data. Full audit trail.

Consultants need to defend their findings. This makes every
answer bulletproof with full source attribution and SQL transparency.

Usage:
    builder = CitationBuilder()
    builder.add_citation(
        claim="847 active employees",
        source_table="employees",
        sql="SELECT COUNT(*) FROM employees WHERE status='A'"
    )
    audit_trail = builder.build_audit_trail()
"""

import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CitationBuilder:
    """
    Citation & Audit Trail Builder - Every claim backed by data.
    
    Consultants need to defend their findings. This makes every
    answer bulletproof with full source attribution and SQL transparency.
    """
    
    def __init__(self):
        self.citations: List[Dict] = []
        self.sql_executed: List[str] = []
    
    def add_citation(
        self,
        claim: str,
        source_table: str,
        source_column: Optional[str] = None,
        sql: Optional[str] = None,
        row_count: Optional[int] = None,
        confidence: float = 1.0
    ) -> None:
        """
        Add a citation for a claim.
        
        Args:
            claim: The claim being made
            source_table: Source table name
            source_column: Relevant column(s)
            sql: SQL query executed
            row_count: Number of rows supporting claim
            confidence: Confidence level (0-1)
        """
        citation = {
            'claim': claim,
            'source_table': source_table.split('__')[-1] if '__' in source_table else source_table,
            'full_table': source_table,
            'source_column': source_column,
            'sql': sql,
            'row_count': row_count,
            'confidence': confidence,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.citations.append(citation)
        
        if sql and sql not in self.sql_executed:
            self.sql_executed.append(sql)
    
    def build_audit_trail(self) -> Dict:
        """Build complete audit trail."""
        return {
            'citations': self.citations,
            'sql_queries': self.sql_executed,
            'total_sources': len(set(c['full_table'] for c in self.citations)),
            'generated_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def format_for_display(self) -> str:
        """Format citations for display in response."""
        if not self.citations:
            return ""
        
        lines = ["\n---", "📍 **Sources & Audit Trail**"]
        
        for i, citation in enumerate(self.citations, 1):
            source_info = f"• {citation['source_table']}"
            if citation['source_column']:
                source_info += f" → {citation['source_column']}"
            if citation['row_count']:
                source_info += f" ({citation['row_count']:,} rows)"
            lines.append(source_info)
        
        if self.sql_executed:
            lines.append("\n*SQL Executed:*")
            for sql in self.sql_executed[:3]:  # Show max 3
                # Truncate long SQL
                sql_display = sql[:200] + '...' if len(sql) > 200 else sql
                lines.append(f"```sql\n{sql_display}\n```")
        
        return "\n".join(lines)
