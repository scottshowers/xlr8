"""
XLR8 Intelligence Engine - Truth Assembler
===========================================
Phase 3.1: Five Truths Assembly

Assembles all Five Truths into a structured context for synthesis.
This creates the input format that the LLM needs to generate consultative responses.

The Five Truths:
- REALITY: What the data shows (from DuckDB)
- INTENT: What customer wants (from ChromaDB - SOW/requirements)
- CONFIGURATION: How system is configured (from DuckDB - settings tables)
- REFERENCE: Best practices (from ChromaDB - vendor docs)
- REGULATORY: Compliance requirements (from ChromaDB - laws/rules)

Deploy to: backend/utils/intelligence/truth_assembler.py
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from .types import Truth

logger = logging.getLogger(__name__)


# =============================================================================
# TRUTH CONTEXT DATA STRUCTURES
# =============================================================================

@dataclass
class RealityContext:
    """
    What IS - actual data from customer.
    
    Contains SQL query results with metadata for synthesis.
    """
    sql_query: str = ""
    row_count: int = 0
    sample_data: List[Dict] = field(default_factory=list)  # First N rows
    column_names: List[str] = field(default_factory=list)
    aggregates: Dict[str, Any] = field(default_factory=dict)  # count, sum, avg if relevant
    table_name: str = ""
    query_type: str = "list"  # list, count, sum, group, etc.
    
    def is_empty(self) -> bool:
        return self.row_count == 0
    
    def to_prompt_section(self, max_rows: int = 10) -> str:
        """Format for LLM prompt."""
        if self.is_empty():
            return "No matching data found."
        
        parts = []
        parts.append(f"Query: {self.sql_query}")
        parts.append(f"Results: {self.row_count:,} rows")
        
        if self.aggregates:
            agg_str = ", ".join(f"{k}={v:,}" if isinstance(v, (int, float)) else f"{k}={v}" 
                               for k, v in self.aggregates.items())
            parts.append(f"Aggregates: {agg_str}")
        
        if self.sample_data:
            parts.append("\nSample data:")
            for i, row in enumerate(self.sample_data[:max_rows]):
                # Format row compactly
                row_str = ", ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
                parts.append(f"  {i+1}. {row_str}")
            
            if len(self.sample_data) > max_rows:
                parts.append(f"  ... and {len(self.sample_data) - max_rows} more")
        
        return "\n".join(parts)


@dataclass
class IntentContext:
    """
    What customer WANTS - from SOW/requirements documents.
    """
    relevant_requirements: List[str] = field(default_factory=list)
    source_documents: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def is_empty(self) -> bool:
        return len(self.relevant_requirements) == 0
    
    def to_prompt_section(self, max_items: int = 5) -> str:
        """Format for LLM prompt."""
        if self.is_empty():
            return "No customer requirements found for this topic."
        
        parts = []
        for req in self.relevant_requirements[:max_items]:
            parts.append(f"• {req}")
        
        if self.source_documents:
            sources = ", ".join(self.source_documents[:3])
            parts.append(f"\nSources: {sources}")
        
        return "\n".join(parts)


@dataclass
class ConfigurationContext:
    """
    How system is CONFIGURED - from settings tables.
    """
    settings: Dict[str, Any] = field(default_factory=dict)
    source_tables: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def is_empty(self) -> bool:
        return len(self.settings) == 0
    
    def to_prompt_section(self) -> str:
        """Format for LLM prompt."""
        if self.is_empty():
            return "No configuration settings found for this topic."
        
        parts = []
        for key, value in list(self.settings.items())[:10]:
            parts.append(f"• {key}: {value}")
        
        return "\n".join(parts)


@dataclass  
class ReferenceContext:
    """
    What's RECOMMENDED - from vendor docs/best practices.
    """
    relevant_guidance: List[str] = field(default_factory=list)
    source_documents: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def is_empty(self) -> bool:
        return len(self.relevant_guidance) == 0
    
    def to_prompt_section(self, max_items: int = 3) -> str:
        """Format for LLM prompt."""
        if self.is_empty():
            return "No best practice documentation found."
        
        parts = []
        for guidance in self.relevant_guidance[:max_items]:
            parts.append(f"• {guidance}")
        
        if self.source_documents:
            sources = ", ".join(self.source_documents[:3])
            parts.append(f"\nSources: {sources}")
        
        return "\n".join(parts)


@dataclass
class RegulatoryContext:
    """
    What's REQUIRED - from compliance docs.
    """
    relevant_requirements: List[str] = field(default_factory=list)
    jurisdictions: List[str] = field(default_factory=list)  # federal, state:CA, etc.
    source_documents: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def is_empty(self) -> bool:
        return len(self.relevant_requirements) == 0
    
    def to_prompt_section(self, max_items: int = 3) -> str:
        """Format for LLM prompt."""
        if self.is_empty():
            return "No regulatory requirements found for this topic."
        
        parts = []
        if self.jurisdictions:
            parts.append(f"Jurisdictions: {', '.join(self.jurisdictions)}")
            parts.append("")
        
        for req in self.relevant_requirements[:max_items]:
            parts.append(f"• {req}")
        
        if self.source_documents:
            sources = ", ".join(self.source_documents[:3])
            parts.append(f"\nSources: {sources}")
        
        return "\n".join(parts)


@dataclass
class Gap:
    """
    A detected gap between truths.
    """
    gap_type: str           # config_vs_intent, config_vs_reference, config_vs_regulatory, missing_data
    severity: str           # high, medium, low
    topic: str              # What the gap is about
    description: str        # Human-readable description
    recommendation: str     # What to do
    actual_value: Any = None       # What was found
    expected_value: Any = None     # What was expected
    source_truth: str = ""         # Which truth revealed the gap
    
    def to_dict(self) -> Dict:
        return {
            'gap_type': self.gap_type,
            'severity': self.severity,
            'topic': self.topic,
            'description': self.description,
            'recommendation': self.recommendation,
            'actual_value': self.actual_value,
            'expected_value': self.expected_value,
            'source_truth': self.source_truth,
        }


@dataclass
class Citation:
    """
    Source citation for provenance.
    """
    source_type: str        # reality, intent, reference, regulatory
    document_name: str
    page_or_section: str = ""
    relevance_score: float = 0.0
    content_preview: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'source_type': self.source_type,
            'document_name': self.document_name,
            'page_or_section': self.page_or_section,
            'relevance_score': round(self.relevance_score, 3),
            'content_preview': self.content_preview[:200] if self.content_preview else "",
        }


@dataclass
class TruthContext:
    """
    Complete assembled context for synthesis.
    
    This is the structured input for the LLM synthesizer.
    """
    # The question
    question: str
    intent_type: str = "list"     # count, list, compare, validate, etc.
    domain: str = "unknown"       # earnings, deductions, taxes, etc.
    
    # The Five Truths (assembled)
    reality: RealityContext = field(default_factory=RealityContext)
    intent: IntentContext = field(default_factory=IntentContext)
    configuration: ConfigurationContext = field(default_factory=ConfigurationContext)
    reference: ReferenceContext = field(default_factory=ReferenceContext)
    regulatory: RegulatoryContext = field(default_factory=RegulatoryContext)
    
    # Detected gaps
    gaps: List[Gap] = field(default_factory=list)
    
    # Citations
    citations: List[Citation] = field(default_factory=list)
    
    # Metadata
    assembled_at: str = ""
    project: str = ""
    
    def __post_init__(self):
        if not self.assembled_at:
            self.assembled_at = datetime.now().isoformat()
    
    @property
    def has_data(self) -> bool:
        """Check if we have any Reality data."""
        return not self.reality.is_empty()
    
    @property
    def has_context(self) -> bool:
        """Check if we have any supporting context."""
        return (not self.intent.is_empty() or 
                not self.reference.is_empty() or 
                not self.regulatory.is_empty())
    
    @property
    def has_gaps(self) -> bool:
        return len(self.gaps) > 0
    
    @property
    def truths_used(self) -> List[str]:
        """List which truths have content."""
        used = []
        if not self.reality.is_empty():
            used.append('reality')
        if not self.intent.is_empty():
            used.append('intent')
        if not self.configuration.is_empty():
            used.append('configuration')
        if not self.reference.is_empty():
            used.append('reference')
        if not self.regulatory.is_empty():
            used.append('regulatory')
        return used
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON/logging."""
        return {
            'question': self.question,
            'intent_type': self.intent_type,
            'domain': self.domain,
            'truths_used': self.truths_used,
            'reality_rows': self.reality.row_count,
            'gap_count': len(self.gaps),
            'citation_count': len(self.citations),
            'assembled_at': self.assembled_at,
            'project': self.project,
        }


# =============================================================================
# TRUTH ASSEMBLER
# =============================================================================

class TruthAssembler:
    """
    Assembles all Five Truths into structured context for synthesis.
    
    This is the bridge between the gatherers (which collect raw truths)
    and the synthesizer (which generates responses).
    """
    
    def __init__(self):
        logger.info("[ASSEMBLER] TruthAssembler initialized")
    
    def assemble(self,
                 question: str,
                 sql_results: Dict = None,
                 vector_results: Dict = None,
                 reality_truths: List[Truth] = None,
                 intent_truths: List[Truth] = None,
                 configuration_truths: List[Truth] = None,
                 reference_truths: List[Truth] = None,
                 regulatory_truths: List[Truth] = None,
                 gaps: List[Gap] = None,
                 citations: List[Citation] = None,
                 project: str = None) -> TruthContext:
        """
        Assemble all truth sources into structured context.
        
        Accepts either:
        - sql_results/vector_results (from Phase 1/2 outputs)
        - Individual truth lists (from gatherers)
        
        Returns:
            TruthContext ready for synthesis
        """
        # Detect intent type from question
        intent_type = self._detect_intent_type(question)
        domain = self._detect_domain(question)
        
        # Build Reality context
        reality = self._build_reality_context(sql_results, reality_truths)
        
        # Build Intent context
        intent = self._build_intent_context(vector_results, intent_truths)
        
        # Build Configuration context
        configuration = self._build_config_context(sql_results, configuration_truths)
        
        # Build Reference context
        reference = self._build_reference_context(vector_results, reference_truths)
        
        # Build Regulatory context
        regulatory = self._build_regulatory_context(vector_results, regulatory_truths)
        
        context = TruthContext(
            question=question,
            intent_type=intent_type,
            domain=domain,
            reality=reality,
            intent=intent,
            configuration=configuration,
            reference=reference,
            regulatory=regulatory,
            gaps=gaps or [],
            citations=citations or [],
            project=project or "",
        )
        
        logger.info(f"[ASSEMBLER] Assembled: truths={context.truths_used}, "
                   f"gaps={len(context.gaps)}, citations={len(context.citations)}")
        
        return context
    
    def _detect_intent_type(self, question: str) -> str:
        """Detect the intent/query type from the question."""
        q_lower = question.lower()
        
        if any(w in q_lower for w in ['how many', 'count', 'total number']):
            return 'count'
        if any(w in q_lower for w in ['sum', 'total amount', 'add up']):
            return 'sum'
        if any(w in q_lower for w in ['average', 'avg', 'mean']):
            return 'average'
        if any(w in q_lower for w in ['compare', 'versus', 'vs', 'difference']):
            return 'compare'
        if any(w in q_lower for w in ['validate', 'verify', 'correct', 'check']):
            return 'validate'
        if any(w in q_lower for w in ['group by', 'breakdown', 'by state', 'by company']):
            return 'group'
        if any(w in q_lower for w in ['most', 'highest', 'top', 'least', 'lowest', 'bottom']):
            return 'superlative'
        if any(w in q_lower for w in ['list', 'show', 'what are', 'which']):
            return 'list'
        
        return 'list'  # Default
    
    def _detect_domain(self, question: str) -> str:
        """Detect the domain from the question."""
        q_lower = question.lower()
        
        domain_patterns = {
            'earnings': ['earning', 'pay code', 'salary', 'wage', 'compensation'],
            'deductions': ['deduction', 'benefit', '401k', 'health', 'insurance'],
            'taxes': ['tax', 'futa', 'suta', 'fit', 'sit', 'withhold'],
            'employees': ['employee', 'worker', 'staff', 'headcount', 'personnel'],
            'locations': ['location', 'site', 'office', 'address'],
            'jobs': ['job', 'position', 'role', 'title'],
            'compliance': ['compliance', 'audit', 'regulation', 'rule'],
            'payroll': ['payroll', 'pay run', 'check', 'payment'],
        }
        
        for domain, patterns in domain_patterns.items():
            if any(p in q_lower for p in patterns):
                return domain
        
        return 'general'
    
    def _build_reality_context(self, sql_results: Dict = None, 
                               reality_truths: List[Truth] = None) -> RealityContext:
        """Build Reality context from SQL results or truths."""
        context = RealityContext()
        
        # Try SQL results first
        if sql_results:
            context.sql_query = sql_results.get('sql', '')
            context.row_count = sql_results.get('row_count', 0)
            context.sample_data = sql_results.get('data', [])[:100]  # Limit sample
            context.column_names = sql_results.get('columns', [])
            context.table_name = sql_results.get('table', '')
            context.query_type = sql_results.get('query_type', 'list')
            
            # Extract aggregates if present
            if sql_results.get('aggregates'):
                context.aggregates = sql_results['aggregates']
            elif context.query_type in ['count', 'sum', 'average'] and context.sample_data:
                # Extract from first row
                first_row = context.sample_data[0] if context.sample_data else {}
                for k, v in first_row.items():
                    if isinstance(v, (int, float)):
                        context.aggregates[k] = v
            
            return context
        
        # Fall back to reality truths
        if reality_truths:
            for truth in reality_truths:
                if isinstance(truth.content, dict):
                    rows = truth.content.get('rows', [])
                    if rows:
                        context.row_count = len(rows)
                        context.sample_data = rows[:100]
                        context.column_names = truth.content.get('columns', [])
                        context.table_name = truth.content.get('table', '')
                        context.query_type = truth.content.get('query_type', 'list')
                        break
        
        return context
    
    def _build_intent_context(self, vector_results: Dict = None,
                              intent_truths: List[Truth] = None) -> IntentContext:
        """Build Intent context from vector results or truths."""
        context = IntentContext()
        
        # Try vector results first
        if vector_results and 'intent' in vector_results:
            intent_chunks = vector_results['intent']
            for chunk in intent_chunks[:5]:
                if isinstance(chunk, dict):
                    text = chunk.get('content', '') or chunk.get('text', '')
                    if text:
                        context.relevant_requirements.append(text[:500])
                    doc = chunk.get('metadata', {}).get('filename', '')
                    if doc and doc not in context.source_documents:
                        context.source_documents.append(doc)
                    context.confidence = max(context.confidence, 
                                            chunk.get('relevance', 0.0))
            return context
        
        # Fall back to intent truths
        if intent_truths:
            for truth in intent_truths:
                text = self._extract_text(truth.content)
                if text:
                    context.relevant_requirements.append(text[:500])
                if truth.source_name and truth.source_name not in context.source_documents:
                    context.source_documents.append(truth.source_name)
                context.confidence = max(context.confidence, truth.confidence)
        
        return context
    
    def _build_config_context(self, sql_results: Dict = None,
                              config_truths: List[Truth] = None) -> ConfigurationContext:
        """Build Configuration context from truths."""
        context = ConfigurationContext()
        
        if config_truths:
            for truth in config_truths:
                if isinstance(truth.content, dict):
                    # Extract settings from truth
                    for k, v in truth.content.items():
                        if k not in ['rows', 'columns', 'sql']:
                            context.settings[k] = v
                if truth.source_name and truth.source_name not in context.source_tables:
                    context.source_tables.append(truth.source_name)
                context.confidence = max(context.confidence, truth.confidence)
        
        return context
    
    def _build_reference_context(self, vector_results: Dict = None,
                                 reference_truths: List[Truth] = None) -> ReferenceContext:
        """Build Reference context from vector results or truths."""
        context = ReferenceContext()
        
        # Try vector results first
        if vector_results and 'reference' in vector_results:
            ref_chunks = vector_results['reference']
            for chunk in ref_chunks[:5]:
                if isinstance(chunk, dict):
                    text = chunk.get('content', '') or chunk.get('text', '')
                    if text:
                        context.relevant_guidance.append(text[:500])
                    doc = chunk.get('metadata', {}).get('filename', '')
                    if doc and doc not in context.source_documents:
                        context.source_documents.append(doc)
                    context.confidence = max(context.confidence,
                                            chunk.get('relevance', 0.0))
            return context
        
        # Fall back to reference truths
        if reference_truths:
            for truth in reference_truths:
                text = self._extract_text(truth.content)
                if text:
                    context.relevant_guidance.append(text[:500])
                if truth.source_name and truth.source_name not in context.source_documents:
                    context.source_documents.append(truth.source_name)
                context.confidence = max(context.confidence, truth.confidence)
        
        return context
    
    def _build_regulatory_context(self, vector_results: Dict = None,
                                  regulatory_truths: List[Truth] = None) -> RegulatoryContext:
        """Build Regulatory context from vector results or truths."""
        context = RegulatoryContext()
        
        # Try vector results first
        if vector_results and 'regulatory' in vector_results:
            reg_chunks = vector_results['regulatory']
            for chunk in reg_chunks[:5]:
                if isinstance(chunk, dict):
                    text = chunk.get('content', '') or chunk.get('text', '')
                    if text:
                        context.relevant_requirements.append(text[:500])
                    doc = chunk.get('metadata', {}).get('filename', '')
                    if doc and doc not in context.source_documents:
                        context.source_documents.append(doc)
                    # Extract jurisdiction
                    meta = chunk.get('metadata', {})
                    jurisdiction = meta.get('jurisdiction', '')
                    if jurisdiction and jurisdiction not in context.jurisdictions:
                        context.jurisdictions.append(jurisdiction)
                    context.confidence = max(context.confidence,
                                            chunk.get('relevance', 0.0))
            return context
        
        # Fall back to regulatory truths
        if regulatory_truths:
            for truth in regulatory_truths:
                text = self._extract_text(truth.content)
                if text:
                    context.relevant_requirements.append(text[:500])
                if truth.source_name and truth.source_name not in context.source_documents:
                    context.source_documents.append(truth.source_name)
                # Extract jurisdiction from metadata
                jurisdiction = truth.metadata.get('jurisdiction', '')
                if jurisdiction and jurisdiction not in context.jurisdictions:
                    context.jurisdictions.append(jurisdiction)
                context.confidence = max(context.confidence, truth.confidence)
        
        return context
    
    def _extract_text(self, content: Any) -> str:
        """Extract text from various content formats."""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return content.get('text', '') or content.get('content', '') or str(content)
        return str(content)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_assembler_instance: Optional[TruthAssembler] = None

def get_assembler() -> TruthAssembler:
    """Get the singleton TruthAssembler instance."""
    global _assembler_instance
    if _assembler_instance is None:
        _assembler_instance = TruthAssembler()
    return _assembler_instance


def assemble_truths(question: str, **kwargs) -> TruthContext:
    """Convenience function to assemble truths."""
    assembler = get_assembler()
    return assembler.assemble(question, **kwargs)
