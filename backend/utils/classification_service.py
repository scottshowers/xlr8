"""
Classification Service - FIVE TRUTHS Transparency Layer
========================================================

Deploy to: backend/utils/classification_service.py

PURPOSE:
This service provides COMPLETE VISIBILITY into how data was classified.
Users need to see exactly what was captured, how it was classified, and WHY.
Without this transparency, there is no trust in the platform.

PROVIDES:
1. Table Classification Report - what was captured for structured data
2. Chunk Classification Report - what was captured for semantic data
3. Routing Transparency - why a table/chunk was selected for a query

Author: XLR8 Team
Version: 1.0.0
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ColumnClassification:
    """Classification details for a single column."""
    column_name: str
    data_type: str  # VARCHAR, INTEGER, etc.
    inferred_type: str  # categorical, numeric, date, text, boolean
    total_count: int
    null_count: int
    fill_rate: float  # percentage
    distinct_count: int
    is_categorical: bool
    is_likely_key: bool
    
    # The actual values captured (CRITICAL for transparency)
    distinct_values: List[str] = field(default_factory=list)
    value_distribution: Dict[str, int] = field(default_factory=dict)
    sample_values: List[str] = field(default_factory=list)
    
    # Classification result
    filter_category: Optional[str] = None  # status, company, location, etc.
    filter_priority: int = 0
    classification_reason: Optional[str] = None
    matched_lookup: Optional[str] = None
    
    # For numeric columns
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    
    # For date columns
    min_date: Optional[str] = None
    max_date: Optional[str] = None


@dataclass
class RelationshipClassification:
    """Classification details for a detected relationship."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str  # N:1, 1:N, 1:1
    confidence: float
    match_percentage: float
    detection_reason: str
    sample_matches: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TableClassification:
    """Complete classification report for a table."""
    table_name: str
    display_name: str  # Short, readable name
    source_filename: str
    project_id: Optional[str]
    truth_type: Optional[str]
    
    # Metrics
    row_count: int
    column_count: int
    created_at: Optional[str] = None
    
    # Classification details
    columns: List[ColumnClassification] = field(default_factory=list)
    relationships: List[RelationshipClassification] = field(default_factory=list)
    
    # Domain classification
    detected_domain: Optional[str] = None  # tax, payroll, hr, etc.
    domain_confidence: float = 0.0
    domain_reason: Optional[str] = None
    
    # Query routing info
    routing_keywords: List[str] = field(default_factory=list)  # Words that will route here
    routing_boost_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChunkClassification:
    """Classification details for a semantic chunk."""
    chunk_id: str
    document_name: str
    chunk_index: int
    chunk_text: str  # Preview (first 500 chars)
    full_length: int
    
    # Metadata captured
    truth_type: Optional[str] = None
    project_id: Optional[str] = None
    structure: Optional[str] = None  # tabular, code, hierarchical, linear, mixed
    strategy: Optional[str] = None  # chunking strategy used
    chunk_type: Optional[str] = None
    parent_section: Optional[str] = None
    has_header: bool = False
    
    # Position info
    position: Optional[str] = None  # "3/15" format
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class DocumentChunks:
    """All chunks for a document."""
    document_name: str
    project_id: Optional[str]
    truth_type: Optional[str]
    total_chunks: int
    chunks: List[ChunkClassification] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class QueryRoutingDecision:
    """Transparency into why tables/chunks were selected for a query."""
    query: str
    timestamp: str
    
    # Table selection
    tables_considered: List[Dict[str, Any]] = field(default_factory=list)  # {table, score, reasons}
    tables_selected: List[str] = field(default_factory=list)
    
    # Chunk selection
    chunks_retrieved: List[Dict[str, Any]] = field(default_factory=list)  # {chunk_id, distance, metadata}
    
    # SQL generated
    sql_generated: Optional[str] = None
    sql_tables_used: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# CLASSIFICATION SERVICE
# =============================================================================

class ClassificationService:
    """
    Service for gathering and exposing classification data.
    
    This is the SINGLE SOURCE OF TRUTH for understanding what the system captured
    and how it will be used for query routing.
    """
    
    def __init__(self, structured_handler=None, rag_handler=None):
        """
        Initialize with handlers.
        
        Args:
            structured_handler: DuckDB handler instance
            rag_handler: ChromaDB handler instance
        """
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        
        # Cache for routing decisions (last N queries)
        self._routing_cache: List[QueryRoutingDecision] = []
        self._max_routing_cache = 50
    
    # =========================================================================
    # TABLE CLASSIFICATION
    # =========================================================================
    
    def get_table_classification(
        self, 
        table_name: str, 
        project_id: Optional[str] = None
    ) -> Optional[TableClassification]:
        """
        Get complete classification report for a table.
        
        Returns everything the system captured about this table:
        - Column types and values
        - Classifications assigned
        - Relationships detected
        - How queries will route to this table
        """
        if not self.structured_handler or not self.structured_handler.conn:
            logger.error("[CLASSIFICATION] No structured handler available")
            return None
        
        try:
            conn = self.structured_handler.conn
            
            # Get table metadata - include display_name
            metadata = conn.execute("""
                SELECT table_name, display_name, project, file_name, row_count, column_count, created_at, truth_type
                FROM _schema_metadata
                WHERE table_name = ?
            """, [table_name]).fetchone()
            
            if not metadata:
                logger.warning(f"[CLASSIFICATION] Table {table_name} not found in metadata")
                return None
            
            table_name_db, display_name, project, filename, row_count, col_count, created_at, truth_type = metadata
            
            # Get column profiles
            columns = self._get_column_classifications(conn, table_name)
            
            # Get relationships
            relationships = self._get_relationship_classifications(conn, table_name)
            
            # Determine domain from column values
            domain, domain_confidence, domain_reason = self._detect_domain(columns)
            
            # Build routing keywords
            routing_keywords = self._extract_routing_keywords(columns)
            
            # Build routing boost reasons
            routing_reasons = self._get_routing_boost_reasons(columns)
            
            # Use display_name from DB, or generate if not set
            if not display_name:
                display_name = self._create_display_name(table_name, filename)
            
            return TableClassification(
                table_name=table_name,
                display_name=display_name,
                source_filename=filename or table_name,
                project_id=project,
                truth_type=truth_type,
                row_count=row_count or 0,
                column_count=col_count or len(columns),
                created_at=str(created_at) if created_at else None,
                columns=columns,
                relationships=relationships,
                detected_domain=domain,
                domain_confidence=domain_confidence,
                domain_reason=domain_reason,
                routing_keywords=routing_keywords,
                routing_boost_reasons=routing_reasons
            )
            
        except Exception as e:
            logger.error(f"[CLASSIFICATION] Error getting table classification: {e}")
            return None
    
    def _get_column_classifications(
        self, 
        conn, 
        table_name: str
    ) -> List[ColumnClassification]:
        """Get classification details for all columns in a table."""
        try:
            profiles = conn.execute("""
                SELECT 
                    column_name, original_dtype, inferred_type,
                    total_count, null_count, distinct_count,
                    is_categorical, is_likely_key,
                    distinct_values, value_distribution, sample_values,
                    filter_category, filter_priority,
                    min_value, max_value, mean_value,
                    min_date, max_date
                FROM _column_profiles
                WHERE LOWER(table_name) = LOWER(?)
                ORDER BY column_name
            """, [table_name]).fetchall()
            
            columns = []
            for row in profiles:
                (col_name, dtype, inferred, total, nulls, distinct,
                 is_cat, is_key, distinct_vals, val_dist, samples,
                 filter_cat, filter_pri, min_v, max_v, mean_v,
                 min_d, max_d) = row
                
                # Parse JSON fields
                distinct_values = []
                if distinct_vals:
                    try:
                        distinct_values = json.loads(distinct_vals) if isinstance(distinct_vals, str) else distinct_vals
                    except:
                        pass
                
                value_distribution = {}
                if val_dist:
                    try:
                        value_distribution = json.loads(val_dist) if isinstance(val_dist, str) else val_dist
                    except:
                        pass
                
                sample_values = []
                if samples:
                    try:
                        sample_values = json.loads(samples) if isinstance(samples, str) else samples
                    except:
                        pass
                
                # Calculate fill rate
                fill_rate = ((total - nulls) / total * 100) if total and total > 0 else 0
                
                # Determine classification reason
                classification_reason = self._determine_classification_reason(
                    col_name, filter_cat, distinct_values, filter_pri
                )
                
                columns.append(ColumnClassification(
                    column_name=col_name,
                    data_type=dtype or 'VARCHAR',
                    inferred_type=inferred or 'text',
                    total_count=total or 0,
                    null_count=nulls or 0,
                    fill_rate=round(fill_rate, 1),
                    distinct_count=distinct or 0,
                    is_categorical=bool(is_cat),
                    is_likely_key=bool(is_key),
                    distinct_values=distinct_values[:50] if distinct_values else [],  # Limit for display
                    value_distribution=dict(list(value_distribution.items())[:20]) if value_distribution else {},
                    sample_values=sample_values[:10] if sample_values else [],
                    filter_category=filter_cat,
                    filter_priority=filter_pri or 0,
                    classification_reason=classification_reason,
                    min_value=min_v,
                    max_value=max_v,
                    mean_value=mean_v,
                    min_date=min_d,
                    max_date=max_d
                ))
            
            return columns
            
        except Exception as e:
            logger.error(f"[CLASSIFICATION] Error getting column profiles: {e}")
            return []
    
    def _get_relationship_classifications(
        self, 
        conn, 
        table_name: str
    ) -> List[RelationshipClassification]:
        """Get relationship details for a table."""
        try:
            # Check if relationships table exists
            try:
                rels = conn.execute("""
                    SELECT 
                        from_table, from_column, to_table, to_column,
                        relationship_type, confidence, match_percentage,
                        detection_method
                    FROM _intelligence_relationships
                    WHERE LOWER(from_table) = LOWER(?) OR LOWER(to_table) = LOWER(?)
                """, [table_name, table_name]).fetchall()
            except:
                return []
            
            relationships = []
            for row in rels:
                (from_t, from_c, to_t, to_c, rel_type, conf, match_pct, method) = row
                
                relationships.append(RelationshipClassification(
                    from_table=from_t,
                    from_column=from_c,
                    to_table=to_t,
                    to_column=to_c,
                    relationship_type=rel_type or 'N:1',
                    confidence=conf or 0.0,
                    match_percentage=match_pct or 0.0,
                    detection_reason=method or 'Column name matching'
                ))
            
            return relationships
            
        except Exception as e:
            logger.error(f"[CLASSIFICATION] Error getting relationships: {e}")
            return []
    
    def _determine_classification_reason(
        self,
        column_name: str,
        filter_category: Optional[str],
        distinct_values: List[str],
        filter_priority: int
    ) -> str:
        """Determine WHY a column was classified a certain way."""
        if not filter_category:
            return "No filter category assigned - not enough distinct values or no pattern match"
        
        reasons = []
        col_lower = column_name.lower()
        
        # Check column name hints
        category_hints = {
            'status': ['status', 'employment_status', 'active'],
            'company': ['company', 'legal_entity', 'employer'],
            'organization': ['department', 'dept', 'division', 'cost_center'],
            'location': ['state', 'location', 'site', 'region'],
            'pay_type': ['hourly_salary', 'pay_type', 'flsa', 'exempt'],
            'employee_type': ['employee_type', 'worker_type'],
            'job': ['job_code', 'job_title', 'position']
        }
        
        if filter_category in category_hints:
            for hint in category_hints[filter_category]:
                if hint in col_lower:
                    reasons.append(f"Column name contains '{hint}'")
                    break
        
        if filter_priority >= 80:
            reasons.append(f"High priority ({filter_priority}) - likely core dimension")
        
        if distinct_values and len(distinct_values) <= 10:
            reasons.append(f"Low cardinality ({len(distinct_values)} values) - good for filtering")
        
        if not reasons:
            reasons.append("Matched lookup table values or pattern detection")
        
        return "; ".join(reasons)
    
    def _detect_domain(
        self, 
        columns: List[ColumnClassification]
    ) -> tuple:
        """Detect the domain (tax, payroll, hr, etc.) from column values."""
        domain_signals = {
            'tax': ['sui', 'futa', 'sit', 'fica', 'withholding', 'w2', 'tax_code', 'tax_type'],
            'payroll': ['earnings', 'deduction', 'gross', 'net', 'pay_period', 'check_date'],
            'hr': ['employee', 'hire_date', 'termination', 'department', 'position'],
            'benefits': ['benefit', 'coverage', 'plan', 'enrollment', 'premium'],
            'time': ['hours', 'timecard', 'punch', 'overtime', 'pto', 'absence']
        }
        
        domain_scores = {d: 0 for d in domain_signals}
        
        for col in columns:
            col_lower = col.column_name.lower()
            values_lower = [str(v).lower() for v in col.distinct_values[:20]]
            
            for domain, signals in domain_signals.items():
                for signal in signals:
                    if signal in col_lower:
                        domain_scores[domain] += 2
                    for val in values_lower:
                        if signal in val:
                            domain_scores[domain] += 1
        
        if not any(domain_scores.values()):
            return None, 0.0, "No domain signals detected"
        
        best_domain = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain]
        total_score = sum(domain_scores.values())
        confidence = best_score / total_score if total_score > 0 else 0
        
        # Find what triggered this domain
        triggers = []
        for col in columns:
            col_lower = col.column_name.lower()
            for signal in domain_signals[best_domain]:
                if signal in col_lower:
                    triggers.append(f"Column '{col.column_name}' contains '{signal}'")
                    break
        
        reason = "; ".join(triggers[:3]) if triggers else "Pattern matching on values"
        
        return best_domain, round(confidence, 2), reason
    
    def _extract_routing_keywords(
        self, 
        columns: List[ColumnClassification]
    ) -> List[str]:
        """Extract keywords that will cause queries to route to this table."""
        keywords = set()
        
        for col in columns:
            # Column names are routing keywords
            keywords.add(col.column_name.lower())
            
            # Categorical values are routing keywords
            if col.is_categorical and col.distinct_values:
                for val in col.distinct_values[:20]:
                    val_str = str(val).lower()
                    if len(val_str) >= 2 and len(val_str) <= 30:
                        keywords.add(val_str)
        
        return sorted(list(keywords))[:50]  # Limit for display
    
    def _get_routing_boost_reasons(
        self, 
        columns: List[ColumnClassification]
    ) -> List[str]:
        """Explain what would give this table a scoring boost."""
        reasons = []
        
        categorical_cols = [c for c in columns if c.is_categorical and c.distinct_values]
        if categorical_cols:
            sample_vals = []
            for col in categorical_cols[:3]:
                sample_vals.extend(col.distinct_values[:3])
            reasons.append(f"Queries mentioning {', '.join(sample_vals[:5])} get +80 boost")
        
        filter_cols = [c for c in columns if c.filter_category]
        if filter_cols:
            cats = set(c.filter_category for c in filter_cols)
            reasons.append(f"Filter categories: {', '.join(cats)}")
        
        key_cols = [c for c in columns if c.is_likely_key]
        if key_cols:
            reasons.append(f"Key columns: {', '.join(c.column_name for c in key_cols[:3])}")
        
        return reasons
    
    def _create_display_name(self, table_name: str, filename: Optional[str]) -> str:
        """Create a short, readable display name."""
        # Remove project prefix if present
        parts = table_name.split('_')
        
        # If filename is available, use it
        if filename:
            # Remove extension
            name = filename.rsplit('.', 1)[0]
            # Truncate if too long
            if len(name) > 40:
                return name[:37] + '...'
            return name
        
        # Otherwise clean up table name
        # Skip first part if it looks like a project code (e.g., TEA1000)
        if len(parts) > 1 and parts[0].isupper() and any(c.isdigit() for c in parts[0]):
            parts = parts[1:]
        
        name = '_'.join(parts)
        if len(name) > 40:
            return name[:37] + '...'
        return name
    
    # =========================================================================
    # CHUNK CLASSIFICATION
    # =========================================================================
    
    def get_document_chunks(
        self, 
        document_name: str,
        project_id: Optional[str] = None,
        collection_name: str = "documents"
    ) -> Optional[DocumentChunks]:
        """
        Get all chunks for a document with their classification details.
        """
        if not self.rag_handler:
            logger.error("[CLASSIFICATION] No RAG handler available")
            return None
        
        try:
            collection = self.rag_handler.client.get_collection(name=collection_name)
            
            # Query by document name
            where_filter = {"source": document_name}
            if project_id:
                where_filter = {
                    "$and": [
                        {"source": document_name},
                        {"project_id": project_id}
                    ]
                }
            
            results = collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )
            
            if not results or not results.get('ids'):
                return None
            
            chunks = []
            truth_type = None
            
            for i, (chunk_id, doc, meta) in enumerate(zip(
                results['ids'], 
                results.get('documents', []),
                results.get('metadatas', [])
            )):
                meta = meta or {}
                
                if not truth_type:
                    truth_type = meta.get('truth_type')
                
                chunks.append(ChunkClassification(
                    chunk_id=chunk_id,
                    document_name=document_name,
                    chunk_index=meta.get('chunk_index', i),
                    chunk_text=doc[:500] if doc else '',
                    full_length=len(doc) if doc else 0,
                    truth_type=meta.get('truth_type'),
                    project_id=meta.get('project_id'),
                    structure=meta.get('structure'),
                    strategy=meta.get('strategy'),
                    chunk_type=meta.get('chunk_type'),
                    parent_section=meta.get('parent_section'),
                    has_header=meta.get('has_header', False),
                    position=meta.get('position'),
                    row_start=meta.get('row_start'),
                    row_end=meta.get('row_end'),
                    line_start=meta.get('line_start'),
                    line_end=meta.get('line_end')
                ))
            
            # Sort by chunk index
            chunks.sort(key=lambda x: x.chunk_index)
            
            return DocumentChunks(
                document_name=document_name,
                project_id=project_id,
                truth_type=truth_type,
                total_chunks=len(chunks),
                chunks=chunks
            )
            
        except Exception as e:
            logger.error(f"[CLASSIFICATION] Error getting document chunks: {e}")
            return None
    
    # =========================================================================
    # ROUTING TRANSPARENCY
    # =========================================================================
    
    def record_routing_decision(
        self,
        query: str,
        tables_considered: List[Dict[str, Any]],
        tables_selected: List[str],
        chunks_retrieved: List[Dict[str, Any]],
        sql_generated: Optional[str] = None
    ) -> QueryRoutingDecision:
        """
        Record a routing decision for later inspection.
        
        This should be called by intelligence_engine during query processing.
        """
        decision = QueryRoutingDecision(
            query=query,
            timestamp=datetime.now().isoformat(),
            tables_considered=tables_considered,
            tables_selected=tables_selected,
            chunks_retrieved=chunks_retrieved,
            sql_generated=sql_generated,
            sql_tables_used=self._extract_tables_from_sql(sql_generated) if sql_generated else []
        )
        
        # Add to cache
        self._routing_cache.append(decision)
        
        # Trim cache if needed
        if len(self._routing_cache) > self._max_routing_cache:
            self._routing_cache = self._routing_cache[-self._max_routing_cache:]
        
        return decision
    
    def get_recent_routing_decisions(self, limit: int = 10) -> List[QueryRoutingDecision]:
        """Get recent routing decisions for debugging."""
        return self._routing_cache[-limit:]
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query."""
        if not sql:
            return []
        
        import re
        tables = set()
        
        # Match FROM table_name and JOIN table_name
        patterns = [
            r'FROM\s+([a-zA-Z0-9_]+)',
            r'JOIN\s+([a-zA-Z0-9_]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.update(matches)
        
        return list(tables)
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def get_all_table_classifications(
        self, 
        project_id: Optional[str] = None
    ) -> List[TableClassification]:
        """Get classification summary for all tables in a project."""
        if not self.structured_handler or not self.structured_handler.conn:
            return []
        
        try:
            conn = self.structured_handler.conn
            
            # Get all tables
            if project_id:
                tables = conn.execute("""
                    SELECT DISTINCT table_name
                    FROM _schema_metadata
                    WHERE project = ?
                """, [project_id]).fetchall()
            else:
                tables = conn.execute("""
                    SELECT DISTINCT table_name
                    FROM _schema_metadata
                """).fetchall()
            
            classifications = []
            for (table_name,) in tables:
                classification = self.get_table_classification(table_name, project_id)
                if classification:
                    classifications.append(classification)
            
            return classifications
            
        except Exception as e:
            logger.error(f"[CLASSIFICATION] Error getting all classifications: {e}")
            return []


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_classification_service: Optional[ClassificationService] = None


def get_classification_service(
    structured_handler=None, 
    rag_handler=None
) -> ClassificationService:
    """Get or create the classification service singleton."""
    global _classification_service
    
    if _classification_service is None:
        _classification_service = ClassificationService(structured_handler, rag_handler)
    elif structured_handler:
        _classification_service.structured_handler = structured_handler
    elif rag_handler:
        _classification_service.rag_handler = rag_handler
    
    return _classification_service
