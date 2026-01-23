"""
XLR8 Intelligence Engine v4 - Main Orchestrator
================================================

The brain of XLR8. Thin orchestrator that coordinates:
- Question analysis and mode detection
- Clarification handling (employee status, filters)
- Truth gathering (Reality, Intent, Configuration, Reference, Regulatory)
- Conflict detection
- Response synthesis (Phase 3: SynthesisPipeline)

v4.0 CHANGES (Phase 3 Integration):
- SynthesisPipeline replaces old Synthesizer (2000-line monolith → clean modular)
- Five Truths assembled into structured TruthContext
- Enhanced gap detection (CONFIG_VS_INTENT, CONFIG_VS_REFERENCE, CONFIG_VS_REGULATORY)
- LLM prompts optimized for local models (Mistral/DeepSeek)
- Consultative response patterns

v3.0 CHANGES:
- Context Graph integration for intelligent table selection
- Semantic type detection in queries
- Graph-aware JOIN suggestions via TableSelector
- Passes Context Graph to components for scoped queries

CRITICAL: ALL questions gather ALL Five Truths.
Validation questions especially need all truths to triangulate:
- "Is this tax rate correct?" needs Regulatory + Configuration + Reality
- "Are we compliant?" needs Regulatory + Reference + Reality + Configuration

This is the NEW modular engine replacing the 6000-line monolith.

Deploy to: backend/utils/intelligence/engine.py
"""

import re
import os
import logging
from typing import Dict, List, Optional, Any, Tuple

from .types import (
    Truth, Conflict, Insight, SynthesizedAnswer, IntelligenceMode,
    TruthType
)
from .table_selector import TableSelector
# OLD PATH DISABLED - Import kept for backward compatibility but not used for fallback
from .sql_generator import SQLGenerator

# NEW: Honest failure responses instead of garbage fallback
from .resolution_response import (
    build_cannot_resolve_response,
    build_needs_clarification_response,
    build_no_data_response,
    build_complex_query_response,
    build_system_error_response,
    get_fuzzy_suggestions,
    ResolutionStatus
)
from .synthesis_pipeline import SynthesisPipeline as Synthesizer  # Phase 3: New clean implementation
from .truth_enricher import TruthEnricher
from .consultative_templates import (
    format_count_response,
    format_aggregation_response,
    format_group_by_response,
    format_list_response
)
from .gatherers import (
    RealityGatherer,
    IntentGatherer,
    ConfigurationGatherer,
    ReferenceGatherer,
    RegulatoryGatherer,
    ComplianceGatherer
)

logger = logging.getLogger(__name__)

# Truth Router for query-aware vector search (Phase 2B.2)
TRUTH_ROUTER_AVAILABLE = False
TruthRouter = None
truth_router_instance = None
try:
    from .truth_router import TruthRouter, get_router
    truth_router_instance = get_router()
    TRUTH_ROUTER_AVAILABLE = True
    logger.info("✅ TruthRouter loaded for query-aware vector search")
except ImportError as e:
    logger.warning(f"TruthRouter not available: {e}")

# Source Prioritizer for authority-based re-ranking (Phase 2B.3)
SOURCE_PRIORITIZER_AVAILABLE = False
source_prioritizer_instance = None
try:
    from .source_prioritizer import SourcePrioritizer, get_prioritizer
    source_prioritizer_instance = get_prioritizer()
    SOURCE_PRIORITIZER_AVAILABLE = True
    logger.info("✅ SourcePrioritizer loaded for authority-based ranking")
except ImportError as e:
    logger.warning(f"SourcePrioritizer not available: {e}")

# Relevance Scorer for multi-factor scoring and filtering (Phase 2B.4)
RELEVANCE_SCORER_AVAILABLE = False
relevance_scorer_instance = None
try:
    from .relevance_scorer import RelevanceScorer, get_scorer
    relevance_scorer_instance = get_scorer()
    RELEVANCE_SCORER_AVAILABLE = True
    logger.info("✅ RelevanceScorer loaded for multi-factor relevance scoring")
except ImportError as e:
    logger.warning(f"RelevanceScorer not available: {e}")

# Citation Tracker for source provenance (Phase 2B.5)
CITATION_TRACKER_AVAILABLE = False
CitationCollector = None
try:
    from .citation_tracker import CitationCollector, collect_citations_from_truths
    CITATION_TRACKER_AVAILABLE = True
    logger.info("✅ CitationTracker loaded for source provenance")
except ImportError as e:
    logger.warning(f"CitationTracker not available: {e}")

# Gap Detector for missing truth coverage (Phase 2B.6)
GAP_DETECTOR_AVAILABLE = False
GapDetector = None
gap_detector_instance = None
try:
    from .gap_detector import GapDetector, get_detector as get_gap_detector
    GAP_DETECTOR_AVAILABLE = True
    logger.info("✅ GapDetector loaded for gap detection")
except ImportError as e:
    logger.warning(f"GapDetector not available: {e}")

# Term Index + SQL Assembler - the NEW deterministic path
# Must be after logger is defined
DETERMINISTIC_PATH_AVAILABLE = False
TermIndex = None
SQLAssembler = None
AssemblerIntent = None
parse_intent = None
try:
    from .term_index import TermIndex
    from .sql_assembler import SQLAssembler, QueryIntent as AssemblerIntent, MultiHopRequest
    from .query_resolver import parse_intent
    DETERMINISTIC_PATH_AVAILABLE = True
    logger.warning("[ENGINE-V2] ✅ Deterministic path AVAILABLE (TermIndex + SQLAssembler)")
except ImportError as e:
    logger.warning(f"[ENGINE-V2] ❌ Deterministic path NOT available: {e}")

# Evolution 10: Relationship Resolver for multi-hop queries
RELATIONSHIP_RESOLVER_AVAILABLE = False
RelationshipResolver = None
try:
    from .relationship_resolver import RelationshipResolver, detect_multi_hop_query
    RELATIONSHIP_RESOLVER_AVAILABLE = True
    logger.warning("[ENGINE-V2] ✅ RelationshipResolver AVAILABLE (Multi-Hop Queries)")
except ImportError as e:
    logger.warning(f"[ENGINE-V2] ❌ RelationshipResolver NOT available: {e}")

__version__ = "10.1.0"  # v10.1: Multi-hop relationships support

# Try to load Project Intelligence
PROJECT_INTELLIGENCE_AVAILABLE = False
get_project_intelligence = None
try:
    from backend.utils.project_intelligence import get_project_intelligence
    PROJECT_INTELLIGENCE_AVAILABLE = True
    logger.info("[ENGINE-V2] ProjectIntelligence available")
except ImportError:
    try:
        from utils.project_intelligence import get_project_intelligence
        PROJECT_INTELLIGENCE_AVAILABLE = True
        logger.info("[ENGINE-V2] ProjectIntelligence available (alt import)")
    except ImportError:
        logger.warning("[ENGINE-V2] ProjectIntelligence not available")

# Try to load IntelligentScoping
SCOPING_AVAILABLE = False
analyze_question_scope = None
try:
    from backend.utils.intelligent_scoping import analyze_question_scope
    SCOPING_AVAILABLE = True
    logger.info("[ENGINE-V2] IntelligentScoping loaded")
except ImportError:
    try:
        from utils.intelligent_scoping import analyze_question_scope
        SCOPING_AVAILABLE = True
        logger.info("[ENGINE-V2] IntelligentScoping loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] IntelligentScoping not available")

# Try to load ConsultativeSynthesizer
SYNTHESIS_AVAILABLE = False
ConsultativeSynthesizer = None
try:
    from backend.utils.consultative_synthesis import ConsultativeSynthesizer
    SYNTHESIS_AVAILABLE = True
    logger.info("[ENGINE-V2] ConsultativeSynthesizer loaded")
except ImportError:
    try:
        from utils.consultative_synthesis import ConsultativeSynthesizer
        SYNTHESIS_AVAILABLE = True
        logger.info("[ENGINE-V2] ConsultativeSynthesizer loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ConsultativeSynthesizer not available")

# Try to load ComparisonEngine
COMPARISON_AVAILABLE = False
ComparisonEngine = None
try:
    from utils.features.comparison_engine import ComparisonEngine
    COMPARISON_AVAILABLE = True
    logger.info("[ENGINE-V2] ComparisonEngine loaded")
except ImportError:
    try:
        from backend.utils.features.comparison_engine import ComparisonEngine
        COMPARISON_AVAILABLE = True
        logger.info("[ENGINE-V2] ComparisonEngine loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ComparisonEngine not available")

# Try to load ComplianceEngine
COMPLIANCE_ENGINE_AVAILABLE = False
run_compliance_check = None
try:
    from backend.utils.compliance_engine import run_compliance_check
    COMPLIANCE_ENGINE_AVAILABLE = True
    logger.info("[ENGINE-V2] ComplianceEngine loaded")
except ImportError:
    try:
        from utils.compliance_engine import run_compliance_check
        COMPLIANCE_ENGINE_AVAILABLE = True
        logger.info("[ENGINE-V2] ComplianceEngine loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ComplianceEngine not available")

# Try to load ProjectIntelligence for organizational metrics
PROJECT_INTELLIGENCE_AVAILABLE = False
get_project_intelligence = None
try:
    from backend.utils.project_intelligence import get_project_intelligence
    PROJECT_INTELLIGENCE_AVAILABLE = True
    logger.info("[ENGINE-V2] ProjectIntelligence loaded")
except ImportError:
    try:
        from utils.project_intelligence import get_project_intelligence
        PROJECT_INTELLIGENCE_AVAILABLE = True
        logger.info("[ENGINE-V2] ProjectIntelligence loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ProjectIntelligence not available")


class IntelligenceEngineV2:
    """
    The brain of XLR8 - modular edition.
    
    Orchestrates the Five Truths:
    1. REALITY - What the data actually shows (DuckDB)
    2. INTENT - What the customer says they want (ChromaDB)
    3. CONFIGURATION - How they've configured the system (DuckDB)
    4. REFERENCE - Product docs, implementation standards (ChromaDB)
    5. REGULATORY - Laws, compliance requirements (ChromaDB)
    
    CRITICAL: ALL questions gather ALL truths. The synthesizer decides relevance.
    Validation questions ESPECIALLY need all truths to triangulate.
    
    Usage:
        engine = IntelligenceEngineV2("PROJECT123")
        engine.load_context(structured_handler=handler, schema=schema)
        answer = engine.ask("How many active employees?")
    """
    
    # Question patterns that indicate config/validation (not employee data)
    CONFIG_DOMAINS = [
        'workers comp', 'work comp', 'sui ', 'suta', 'futa', 'tax rate',
        'withholding', 'wc rate', 'workers compensation', 'local tax',
        'earnings', 'earning code', 'pay code', 'earning setup',
        'deduction', 'benefit plan', 'deduction setup', 'deductions',
        'gl', 'general ledger', 'gl mapping', 'account mapping',
        'tax jurisdiction', 'jurisdiction setup', 'state setup',
    ]
    
    VALIDATION_KEYWORDS = [
        'correct', 'valid', 'right', 'properly', 'configured',
        'issue', 'problem', 'check', 'verify', 'audit', 'review',
        'accurate', 'wrong', 'error', 'mistake', 'setup', 'setting'
    ]
    
    EMPLOYEE_INDICATORS = [
        'employee', 'worker', 'staff', 'personnel', 'headcount',
        'how many people', 'count of people', 'list of employees', 
        'terminated', 'active employee', 'hired', 'tenure'
    ]
    
    # Pure Chat - Definitional/conceptual questions (no data needed)
    # Code word to enable Claude API fallback for Pure Chat
    PURE_CHAT_CODE_WORD = "[ASTROS2X]"
    
    # Patterns that indicate a definitional/conceptual question
    PURE_CHAT_PATTERNS = [
        'what is a ', 'what is an ', 'what are ',
        'what does ', 'what do ',
        'how does ', 'how do ',
        'explain ', 'define ', 'describe ',
        'tell me about ', 'what\'s the difference between',
        'what is the purpose of ', 'why would ',
        'when should ', 'when would ',
        'can you explain ', 'help me understand ',
    ]
    
    # Indicators that the question needs actual data (NOT pure chat)
    DATA_INDICATORS = [
        # Quantitative
        'how many', 'count', 'total', 'sum', 'average',
        # Inventory/listing
        'list ', 'show ', 'display ', 'give me ', 'get me ',
        'what are the ', 'what are our ', 'what are my ',
        'do we have', 'do i have', 'does our',
        # Specific lookups - geographic with state names
        ' in texas', ' in california', ' in new york', ' in florida',
        'employees in ', 'workers in ', 'people in ',
        'for john', 'for employee', 'for department',
        # Possessives indicating client data
        'our ', 'my ', 'we have', 'our company',
        # Table/report language
        'table', 'report', 'spreadsheet', 'export',
        # Comparison with data
        'compare our', 'versus our', 'vs our',
    ]
    
    def __init__(self, project_name: str, customer_id: str = None, product_id: str = None):
        """
        Initialize the engine.
        
        Args:
            project_name: Project code (e.g., "TEA1000")
            customer_id: Project UUID for RAG filtering
            product_id: Product type ID for schema loading (e.g., "ukg_pro", "workday_hcm")
        """
        self.project = project_name
        self.customer_id = customer_id
        self.product_id = product_id  # Phase 5F: Multi-product support
        
        # Data handlers
        self.structured_handler = None
        self.rag_handler = None
        self.schema: Dict = {}
        self.relationships: List = []
        
        # Phase 5F: Product schema from registry
        self.product_schema = None
        
        # Filter state
        self.filter_candidates: Dict = {}
        self.confirmed_facts: Dict = {}
        
        # Components
        self.table_selector: Optional[TableSelector] = None
        self.sql_generator: Optional[SQLGenerator] = None
        self.synthesizer: Optional[Synthesizer] = None
        
        # Truth Gatherers
        self.reality_gatherer: Optional[RealityGatherer] = None
        self.intent_gatherer: Optional[IntentGatherer] = None
        self.configuration_gatherer: Optional[ConfigurationGatherer] = None
        self.reference_gatherer: Optional[ReferenceGatherer] = None
        self.regulatory_gatherer: Optional[RegulatoryGatherer] = None
        self.compliance_gatherer: Optional[ComplianceGatherer] = None
        
        # Truth Enricher (LLM Lookups)
        self.truth_enricher: Optional[TruthEnricher] = None
        
        # Pattern cache for learning
        self.pattern_cache = None
        
        # State tracking
        self.last_executed_sql: Optional[str] = None
        self.conversation_history: List[Dict] = []
        self._pending_clarification = None
        self._last_validation_export = None
        
        # v8.0: Project Intelligence - loaded on context load
        self.project_intelligence = None
        self.vocabulary: Dict = {}  # column_name -> {label, values}
        self.dimensions: List[str] = []  # Natural breakdown hierarchy
        self.scope: Dict = {}  # countries, companies, active/termed counts
        self.coverage: Dict = {}  # entity -> {configured, used, pct}
        
        # Initialize LLM synthesizer
        self._llm_synthesizer = None
        if SYNTHESIS_AVAILABLE and ConsultativeSynthesizer:
            try:
                self._llm_synthesizer = ConsultativeSynthesizer(
                    ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    claude_api_key=os.getenv("CLAUDE_API_KEY"),
                    model_preference="auto"
                )
                logger.info("[ENGINE-V2] ConsultativeSynthesizer initialized")
            except Exception as e:
                logger.warning(f"[ENGINE-V2] ConsultativeSynthesizer init failed: {e}")
        
        # Phase 5F: Load product schema if specified
        if product_id:
            self._load_product_schema(product_id)
        
        logger.info(f"[ENGINE-V2] Initialized v{__version__} for project={project_name}, product={product_id}")
    
    def _load_product_schema(self, product_id: str):
        """
        Load product schema from registry (Phase 5F).
        
        This provides domain-aware vocabulary and entity mappings
        for the specific product type.
        """
        try:
            from backend.utils.products import get_product, get_vocabulary_normalizer
            
            product = get_product(product_id)
            if product:
                self.product_schema = product
                self.product_id = product_id
                logger.info(f"[ENGINE-V2] ✅ Product schema loaded: {product.vendor} {product.product} "
                           f"({product.domain_count} domains, {product.hub_count} hubs)")
            else:
                logger.warning(f"[ENGINE-V2] Product not found: {product_id}")
        except ImportError:
            logger.warning("[ENGINE-V2] Product registry not available")
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Failed to load product schema: {e}")
    
    def get_product_domains(self) -> Dict:
        """Get domains for the current product."""
        if self.product_schema:
            return {
                name: {
                    'description': d.description,
                    'hub_count': d.hub_count,
                    'hubs': d.hubs,
                }
                for name, d in self.product_schema.domains.items()
            }
        return {}
    
    def get_product_info(self) -> Dict:
        """Get current product info."""
        if self.product_schema:
            return {
                'product_id': self.product_id,
                'vendor': self.product_schema.vendor,
                'name': self.product_schema.product,
                'category': self.product_schema.category,
                'domain_count': self.product_schema.domain_count,
                'hub_count': self.product_schema.hub_count,
            }
        return {'product_id': None, 'vendor': None, 'name': None}
    
    def load_context(
        self,
        structured_handler=None,
        rag_handler=None,
        schema: Dict = None,
        relationships: List = None,
        filter_candidates: Dict = None
    ):
        """
        Load context and initialize components.
        
        Args:
            structured_handler: DuckDB handler
            rag_handler: ChromaDB/RAG handler
            schema: Schema metadata (tables, columns)
            relationships: Detected table relationships
            filter_candidates: Filter candidate columns by category (optional, extracted from schema if not provided)
        """
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
        
        # =====================================================================
        # v8.0: Load Project Intelligence (computed on upload)
        # This is the BRAIN - vocabulary, dimensions, coverage, findings
        # =====================================================================
        if PROJECT_INTELLIGENCE_AVAILABLE and structured_handler:
            try:
                self.project_intelligence = get_project_intelligence(self.project, structured_handler)
                if self.project_intelligence:
                    self._load_intelligence_context()
                    logger.warning(f"[ENGINE-V2] ✅ Project Intelligence loaded: vocab={len(self.vocabulary)}, dims={len(self.dimensions)}")
            except Exception as e:
                logger.warning(f"[ENGINE-V2] Project Intelligence load failed: {e}")
        
        # Extract filter candidates from schema if not provided explicitly
        self.filter_candidates = filter_candidates or self.schema.get('filter_candidates', {})
        if self.filter_candidates:
            logger.warning(f"[ENGINE-V2] Filter candidates loaded: {list(self.filter_candidates.keys())}")
        
        # Initialize pattern cache
        self._init_pattern_cache()
        
        # Initialize components
        self.table_selector = TableSelector(
            structured_handler=structured_handler,
            filter_candidates=self.filter_candidates,
            project=self.project  # Enable classification metadata loading
        )
        
        self.sql_generator = SQLGenerator(
            structured_handler=structured_handler,
            schema=self.schema,
            table_selector=self.table_selector,
            filter_candidates=self.filter_candidates,
            confirmed_facts=self.confirmed_facts,
            relationships=self.relationships
        )
        
        self.synthesizer = Synthesizer(
            llm_synthesizer=self._llm_synthesizer,
            confirmed_facts=self.confirmed_facts,
            filter_candidates=self.filter_candidates,
            schema=self.schema,
            structured_handler=structured_handler,  # v4.4: For hub usage analysis
            vocabulary=self.vocabulary,  # v8.0: What they call things
            dimensions=self.dimensions,  # v8.0: Breakdown hierarchy
            scope=self.scope,  # v8.0: Who's in the data
            coverage=self.coverage  # v8.0: Config vs used
        )
        
        self.reality_gatherer = RealityGatherer(
            project_name=self.project,
            customer_id=self.customer_id,
            structured_handler=structured_handler,
            schema=self.schema,
            sql_generator=self.sql_generator,
            pattern_cache=self.pattern_cache
        )
        
        # Intent gatherer (ChromaDB - customer documents)
        self.intent_gatherer = IntentGatherer(
            project_name=self.project,
            customer_id=self.customer_id,
            rag_handler=rag_handler
        )
        
        # Configuration gatherer (DuckDB - code tables)
        # Pass table_selector so it can use the same scoring logic
        self.configuration_gatherer = ConfigurationGatherer(
            project_name=self.project,
            customer_id=self.customer_id,
            structured_handler=structured_handler,
            schema=self.schema,
            table_selector=self.table_selector  # Use same selector for consistent scoring
        )
        
        # Global gatherers (Reference Library - no project filter)
        self.reference_gatherer = ReferenceGatherer(
            project_name=self.project,
            customer_id=self.customer_id,
            rag_handler=rag_handler
        )
        
        self.regulatory_gatherer = RegulatoryGatherer(
            project_name=self.project,
            customer_id=self.customer_id,
            rag_handler=rag_handler
        )
        
        self.compliance_gatherer = ComplianceGatherer(
            project_name=self.project,
            customer_id=self.customer_id,
            rag_handler=rag_handler
        )
        
        # Truth Enricher (LLM Lookups) - extracts structured data from raw truths
        self.truth_enricher = TruthEnricher(customer_id=self.customer_id)
        
        # v3.0: Log Context Graph availability
        context_graph_available = False
        if structured_handler and hasattr(structured_handler, 'get_context_graph'):
            try:
                graph = structured_handler.get_context_graph(self.project)
                hub_count = len(graph.get('hubs', []))
                rel_count = len(graph.get('relationships', []))
                if hub_count > 0 or rel_count > 0:
                    context_graph_available = True
                    logger.warning(f"[ENGINE-V2] Context Graph: {hub_count} hubs, {rel_count} relationships")
            except Exception as e:
                logger.debug(f"[ENGINE-V2] Context Graph not available: {e}")
        
        logger.info(f"[ENGINE-V2] Context loaded: {len(self.schema.get('tables', []))} tables, "
                   f"{len(self.filter_candidates)} filter categories, "
                   f"context_graph={'yes' if context_graph_available else 'no'}")
    
    def _init_pattern_cache(self):
        """Initialize SQL pattern cache for learning.
        
        NOTE: Pattern cache module was archived. This is a no-op stub.
        The pattern_cache remains None, which is handled gracefully by
        RealityGatherer (it checks `if self.pattern_cache` before use).
        """
        # Pattern cache feature removed - RealityGatherer handles None gracefully
        pass
    
    def _load_intelligence_context(self):
        """
        v8.0: Extract vocabulary, dimensions, coverage from Project Intelligence.
        
        This transforms raw intelligence data into actionable context:
        - vocabulary: What they call things (org_level_1 = "Division")
        - dimensions: Natural breakdown hierarchy (Country → Company → Division)
        - scope: Who's in the data (countries, companies, active/termed)
        - coverage: What's configured vs used (earnings: 20 config, 8 used)
        """
        if not self.project_intelligence:
            return
        
        pi = self.project_intelligence
        
        # =====================================================================
        # 1. VOCABULARY - Learn what they call things
        # From lookups and column profiles with low cardinality
        # =====================================================================
        try:
            # From lookups (pre-detected code/description pairs)
            if hasattr(pi, 'lookups') and pi.lookups:
                for lookup in pi.lookups:
                    col = lookup.code_column if hasattr(lookup, 'code_column') else None
                    if col:
                        self.vocabulary[col] = {
                            'table': lookup.table_name if hasattr(lookup, 'table_name') else '',
                            'type': 'lookup',
                            'values': list(lookup.lookup_data.keys()) if hasattr(lookup, 'lookup_data') and lookup.lookup_data else []
                        }
            
            # From column profiles (low cardinality = categorical)
            if self.structured_handler:
                try:
                    profiles = self.structured_handler.conn.execute("""
                        SELECT column_name, distinct_count, top_values_json, filter_category
                        FROM _column_profiles
                        WHERE project = ?
                          AND distinct_count BETWEEN 2 AND 50
                          AND top_values_json IS NOT NULL
                        ORDER BY distinct_count
                    """, [self.project]).fetchall()
                    
                    for col_name, distinct_count, values_json, filter_cat in profiles:
                        if col_name not in self.vocabulary:
                            try:
                                import json
                                values = json.loads(values_json) if values_json else []
                                # Infer friendly label from column name
                                label = self._infer_column_label(col_name, values)
                                self.vocabulary[col_name] = {
                                    'label': label,
                                    'type': filter_cat or 'categorical',
                                    'values': values[:20],  # Top 20
                                    'count': distinct_count
                                }
                            except:
                                pass
                except Exception as e:
                    logger.debug(f"[ENGINE-V2] Column profiles load failed: {e}")
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Vocabulary extraction failed: {e}")
        
        # =====================================================================
        # 2. DIMENSIONS - Natural breakdown hierarchy
        # Infer from vocabulary + Context Graph relationships
        # =====================================================================
        try:
            # Standard HCM hierarchy - look for what exists in vocabulary
            dimension_priority = [
                ('country', ['country_code', 'country', 'country_name']),
                ('company', ['company_code', 'company', 'company_id']),
                ('division', ['org_level_1', 'division', 'division_code']),
                ('department', ['org_level_2', 'department', 'department_code', 'dept']),
                ('location', ['location_code', 'location', 'work_location']),
                ('employee_type', ['employee_type', 'emp_type', 'worker_type']),
                ('pay_type', ['pay_type', 'pay_frequency', 'salary_type']),
            ]
            
            vocab_cols = set(self.vocabulary.keys())
            for dim_name, possible_cols in dimension_priority:
                for col in possible_cols:
                    if col in vocab_cols:
                        self.dimensions.append(col)
                        # Store friendly name
                        if col in self.vocabulary:
                            self.vocabulary[col]['dimension'] = dim_name
                        break
            
            logger.debug(f"[ENGINE-V2] Detected dimensions: {self.dimensions}")
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Dimension detection failed: {e}")
        
        # =====================================================================
        # 3. SCOPE - Who's in the data
        # Active vs termed, by country/company
        # =====================================================================
        try:
            if self.structured_handler:
                # Try to get employee counts by status
                try:
                    # Find employee table
                    emp_tables = self.structured_handler.conn.execute("""
                        SELECT table_name FROM _schema_metadata
                        WHERE project = ? AND (
                            entity_type ILIKE '%employee%' OR 
                            table_name ILIKE '%employee%' OR
                            table_name ILIKE '%summary%'
                        ) AND truth_type = 'reality'
                        AND is_current = TRUE
                        LIMIT 1
                    """, [self.project]).fetchone()
                    
                    if emp_tables:
                        emp_table = emp_tables[0]
                        
                        # Get status breakdown
                        status_sql = f"""
                            SELECT 
                                COALESCE(status, 'Unknown') as status,
                                COUNT(*) as cnt
                            FROM "{emp_table}"
                            GROUP BY status
                        """
                        try:
                            status_result = self.structured_handler.conn.execute(status_sql).fetchall()
                            for status, cnt in status_result:
                                status_key = status.lower() if status else 'unknown'
                                if 'active' in status_key or status_key == 'a':
                                    self.scope['active_employees'] = cnt
                                elif 'term' in status_key or status_key == 't':
                                    self.scope['termed_employees'] = cnt
                                else:
                                    self.scope.setdefault('other_status', {})[status] = cnt
                        except:
                            pass
                        
                        # Get country breakdown if available
                        for dim_col in ['country_code', 'country']:
                            try:
                                country_sql = f"""
                                    SELECT "{dim_col}", COUNT(*) as cnt
                                    FROM "{emp_table}"
                                    WHERE "{dim_col}" IS NOT NULL
                                    GROUP BY "{dim_col}"
                                    ORDER BY cnt DESC
                                """
                                country_result = self.structured_handler.conn.execute(country_sql).fetchall()
                                if country_result:
                                    self.scope['by_country'] = {r[0]: r[1] for r in country_result}
                                    break
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"[ENGINE-V2] Employee scope extraction failed: {e}")
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Scope extraction failed: {e}")
        
        # =====================================================================
        # 4. COVERAGE - What's configured vs used
        # From Context Graph hub/spoke analysis
        # =====================================================================
        try:
            if self.structured_handler and hasattr(self.structured_handler, 'get_context_graph'):
                graph = self.structured_handler.get_context_graph(self.project)
                
                for hub in graph.get('hubs', []):
                    semantic_type = hub.get('semantic_type', '')
                    entity_type = hub.get('entity_type', semantic_type)
                    cardinality = hub.get('cardinality', 0)
                    has_reality = hub.get('has_reality_spokes', False)
                    
                    if entity_type:
                        self.coverage[entity_type] = {
                            'configured': cardinality,
                            'has_employee_data': has_reality,
                            'hub_table': hub.get('table', '')
                        }
                
                # Count used codes from relationships
                for rel in graph.get('relationships', []):
                    if rel.get('truth_type') == 'reality':
                        hub_table = rel.get('hub_table', '')
                        spoke_cardinality = rel.get('spoke_cardinality', 0)
                        
                        # Find matching coverage entry
                        for entity, cov in self.coverage.items():
                            if cov.get('hub_table', '').lower() == hub_table.lower():
                                cov['used'] = spoke_cardinality
                                cov['usage_pct'] = round(100 * spoke_cardinality / cov['configured'], 1) if cov['configured'] > 0 else 0
                                break
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Coverage extraction failed: {e}")
        
        logger.warning(f"[ENGINE-V2] Intelligence context loaded: "
                      f"vocab={len(self.vocabulary)}, dims={self.dimensions}, "
                      f"scope={list(self.scope.keys())}, coverage={list(self.coverage.keys())}")
    
    def _infer_column_label(self, col_name: str, values: List) -> str:
        """Infer a friendly label for a column based on name and values."""
        col_lower = col_name.lower()
        
        # Known mappings
        label_map = {
            'org_level_1': 'Division',
            'org_level_2': 'Department', 
            'org_level_3': 'Team',
            'org_level_4': 'Unit',
            'employee_type': 'Employee Type',
            'emp_type': 'Employee Type',
            'pay_type': 'Pay Type',
            'status': 'Status',
            'country_code': 'Country',
            'company_code': 'Company',
            'location_code': 'Location',
            'earnings_group': 'Earnings Group',
            'deduction_group': 'Deduction Group',
        }
        
        if col_lower in label_map:
            return label_map[col_lower]
        
        # Generate from column name
        label = col_name.replace('_', ' ').title()
        return label
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def ask(self, question: str, mode: IntelligenceMode = None,
            context: Dict = None) -> SynthesizedAnswer:
        """
        Answer a question using ALL Five Truths.
        
        CRITICAL: Every question gathers from ALL truth types.
        The synthesizer decides what's relevant, not this method.
        
        This is the main entry point. It:
        1. Analyzes the question to detect mode and domains
        2. Handles clarification requests if needed
        3. Gathers from ALL Truth types (no skipping)
        4. Detects conflicts between truths
        5. Synthesizes a consultative response
        
        Args:
            question: The user's question
            mode: Optional explicit mode
            context: Optional additional context
            
        Returns:
            SynthesizedAnswer with full provenance
        """
        context = context or {}
        q_lower = question.lower()
        
        logger.warning(f"[ENGINE-V2] Question: {question[:80]}...")
        logger.warning(f"[ENGINE-V2] confirmed_facts: {self.confirmed_facts}")
        
        try:
            return self._ask_internal(question, mode, context, q_lower)
        except Exception as e:
            logger.error(f"[ENGINE-V2] FATAL ERROR in ask(): {e}")
            import traceback
            logger.error(f"[ENGINE-V2] Traceback: {traceback.format_exc()}")
            # Return error response instead of crashing
            return SynthesizedAnswer(
                question=question,
                answer=f"I encountered an error processing your question. Please try rephrasing or simplifying your query.",
                confidence=0.0,
                reasoning=[f"Error: {str(e)[:200]}"]
            )
    
    def _ask_internal(self, question: str, mode: IntelligenceMode,
                      context: Dict, q_lower: str) -> SynthesizedAnswer:
        """Internal implementation of ask() with actual logic."""
        
        # STEP 1: Export request check
        try:
            export_result = self._handle_export_request(question, q_lower)
            if export_result:
                return export_result
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in export_request: {e}")
            raise
        
        # =====================================================================
        # STEP 1.5: PURE CHAT - Definitional/conceptual questions
        # Skip data gathering for questions like "what is a benefit class?"
        # Uses Reference docs + Local LLM only (no Claude unless [ASTROS2X])
        # =====================================================================
        try:
            if self._is_pure_chat_question(question, q_lower):
                pure_chat_result = self._handle_pure_chat(question, q_lower)
                if pure_chat_result:
                    logger.warning("[ENGINE-V2] PURE CHAT SUCCESS - returning directly")
                    return pure_chat_result
                else:
                    logger.warning("[ENGINE-V2] Pure Chat failed - continuing to normal flow")
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in pure_chat: {e}")
            # Don't raise - continue to normal flow
        
        # STEP 2: Query Resolver
        # EVOLUTION 6: Skip QueryResolver for negation queries - it doesn't understand NOT/!=
        negation_keywords = ['not ', 'excluding ', 'except ', 'without ']
        has_negation = any(kw in question.lower() for kw in negation_keywords)
        
        # EVOLUTION 8 FIX: Skip QueryResolver for GROUP BY queries
        # QueryResolver's workforce_snapshot always groups by status, not the requested dimension
        # These queries should go through the deterministic path which handles GROUP BY correctly
        group_by_patterns = [' by ', ' per ', ' for each ', ' broken down by ', ' grouped by ']
        has_group_by = any(pattern in question.lower() for pattern in group_by_patterns)
        
        if has_negation:
            logger.warning(f"[ENGINE-V2] Skipping QueryResolver - negation detected in query")
        elif has_group_by:
            logger.warning(f"[ENGINE-V2] Skipping QueryResolver - GROUP BY detected, using deterministic path")
        else:
            try:
                resolver_context = self._try_query_resolver(question)
                if resolver_context:
                    context['resolver'] = resolver_context
                    context['skip_clarification'] = True
                    logger.warning(f"[ENGINE-V2] QueryResolver provided context, skipping clarifications")
                    
                    # =========================================================
                    # CONSULTATIVE PATH: QueryResolver has structured output
                    # Skip deterministic, go straight to LLM synthesis
                    # =========================================================
                    if resolver_context.get('structured_output'):
                        logger.warning(f"[ENGINE-V2] QueryResolver has structured_output - using CONSULTATIVE PATH")
                        try:
                            consultative_result = self._synthesize_with_resolver_context(
                                question=question,
                                resolver_context=resolver_context
                            )
                            if consultative_result:
                                logger.warning(f"[ENGINE-V2] CONSULTATIVE PATH SUCCESS")
                                return consultative_result
                        except Exception as e:
                            logger.error(f"[ENGINE-V2] Error in consultative path: {e}")
                            # Fall through to deterministic path
            except Exception as e:
                logger.error(f"[ENGINE-V2] Error in query_resolver: {e}")
                raise
        
        # =====================================================================
        # STEP 2.5: DETERMINISTIC PATH - Term Index + SQL Assembler
        # This is the PRIMARY PATH for DuckDB queries.
        # NO FALLBACK TO OLD LLM PATH - honest failure instead.
        # =====================================================================
        try:
            deterministic_result = self._try_deterministic_path(question)
            if deterministic_result:
                # Check if this is a structured failure response
                if hasattr(deterministic_result, 'structured_output'):
                    output = deterministic_result.structured_output or {}
                    status = output.get('status', '')
                    
                    # Complex queries need full pipeline - continue to gather all truths
                    if status == 'complex_query':
                        logger.warning(f"[ENGINE-V2] Complex query - continuing to full pipeline")
                        # Fall through to gather Reference/Regulatory/Compliance
                    else:
                        # Success or honest failure - return directly
                        logger.warning(f"[ENGINE-V2] DETERMINISTIC PATH - returning (status={status or 'success'})")
                        return deterministic_result
                else:
                    # Legacy success response
                    logger.warning(f"[ENGINE-V2] DETERMINISTIC PATH SUCCESS - returning directly")
                    return deterministic_result
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in deterministic_path: {e}")
            import traceback
            logger.error(f"[ENGINE-V2] Traceback: {traceback.format_exc()}")
            # Return honest error instead of falling back to garbage generator
            return build_system_error_response(
                question=question,
                error=str(e),
                component="deterministic_path",
                context={"traceback": traceback.format_exc()[:500]}
            )
        
        # STEP 3: Analyze question
        try:
            mode = mode or self._detect_mode(q_lower)
            is_employee_question = self._is_employee_question(q_lower)
            is_validation = self._is_validation_question(q_lower)
            is_config = self._is_config_domain(q_lower)
            
            # Override employee detection for config/validation questions
            # Config questions (tax codes, earnings, deductions, GL) are NOT about employees
            if is_config:
                is_employee_question = False
                logger.warning("[ENGINE-V2] Config domain detected - skipping employee clarification")
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in question_analysis: {e}")
            raise
        
        # STEP 4: Clarification check
        try:
            if is_employee_question and not context.get('skip_clarification'):
                clarification = self._check_clarification_needed(question, q_lower)
                if clarification:
                    return clarification
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in clarification_check: {e}")
            raise
        
        logger.warning(f"[ENGINE-V2] Proceeding with mode={mode.value}, validation={is_validation}, config={is_config}")
        
        # =====================================================================
        # v4.0: INTELLIGENT SCOPING - The Consultant's First Move
        # Before answering, understand the data landscape
        # Skip if QueryResolver already resolved the query
        # =====================================================================
        scope_filter = None
        
        # Check if scope was already provided via clarification
        if self.confirmed_facts.get('scope'):
            scope_value = self.confirmed_facts['scope']
            logger.warning(f"[ENGINE-V2] Scope already confirmed: {scope_value}")
            
            if scope_value != 'all':
                # Parse "dimension:value" format
                if ':' in scope_value:
                    dim, val = scope_value.split(':', 1)
                    scope_filter = {'dimension': dim, 'value': val}
                    logger.warning(f"[ENGINE-V2] Applying scope filter: {scope_filter}")
        
        # Only ask for scoping if not already answered AND not resolved by QueryResolver
        elif SCOPING_AVAILABLE and self.structured_handler and not context.get('skip_clarification'):
            try:
                # Check if this is a scope-sensitive question
                scope_sensitive = any([
                    'list' in q_lower, 'show' in q_lower, 'all' in q_lower,
                    'how many' in q_lower, 'count' in q_lower,
                    is_config, is_validation
                ])
                
                if scope_sensitive:
                    scope_analysis = analyze_question_scope(
                        self.project, 
                        question, 
                        self.structured_handler
                    )
                    
                    if scope_analysis and scope_analysis.needs_clarification:
                        logger.warning(f"[ENGINE-V2] Scoping clarification needed: {len(scope_analysis.segments)} segments")
                        
                        # Build scope options from segments
                        scope_options = []
                        for seg in scope_analysis.segments:
                            scope_options.append({
                                'id': f"{seg.dimension}:{seg.value}",
                                'label': f"{seg.display_name} ({seg.employee_count:,} employees)"
                            })
                        scope_options.append({
                            'id': 'all',
                            'label': f"All ({scope_analysis.total_employees:,} employees) - export to Excel"
                        })
                        
                        # Return the intelligent scoping question as the response
                        return SynthesizedAnswer(
                            question=question,
                            answer=scope_analysis.suggested_question,
                            confidence=0.95,
                            structured_output={
                                'type': 'clarification_needed',  # Use same type as status clarification
                                'questions': [{
                                    'id': 'scope',
                                    'question': f"Which {scope_analysis.segments[0].dimension.replace('_code', '').replace('_', ' ')} should I focus on?",
                                    'type': 'radio',
                                    'options': scope_options
                                }],
                                'domain': scope_analysis.question_domain,
                                'total_employees': scope_analysis.total_employees,
                                'original_question': question
                            },
                            reasoning=[
                                f"Detected {scope_analysis.question_domain} domain",
                                f"Found {len(scope_analysis.segments)} meaningful segments",
                                f"Total {scope_analysis.total_employees:,} employees across segments",
                                "Asking for scope clarification before querying"
                            ]
                        )
                    elif scope_analysis:
                        # Add scope info to analysis context
                        logger.warning(f"[ENGINE-V2] Scope analysis: {scope_analysis.question_domain}, "
                                      f"{scope_analysis.total_employees} employees")
            except Exception as e:
                logger.error(f"[ENGINE-V2] Error in intelligent_scoping: {e}")
                import traceback
                logger.error(f"[ENGINE-V2] Scoping traceback: {traceback.format_exc()}")
        
        # =====================================================================
        # COMPARISON MODE - Use ComparisonEngine for table comparisons
        # =====================================================================
        if mode == IntelligenceMode.COMPARE and COMPARISON_AVAILABLE and self.structured_handler:
            comparison_result = self._handle_comparison(question, q_lower)
            if comparison_result:
                return comparison_result
        
        # Build analysis context
        analysis = {
            'mode': mode,
            'domains': self._detect_domains(q_lower),
            'is_employee_question': is_employee_question,
            'is_validation': is_validation,
            'is_config': is_config,
            'question': question,
            'q_lower': q_lower,
            'scope_filter': scope_filter,  # v4.0: Pass scope filter for SQL generation
            'resolver': context.get('resolver'),  # QueryResolver context if available
            'project': self.project,
            'project_name': self.project
        }
        
        # v3.0: Detect entity scoping from Context Graph
        # If question mentions specific values (e.g., "company ABC"), scope queries
        entity_scope = self._detect_entity_scope(question, q_lower)
        if entity_scope:
            analysis['entity_scope'] = entity_scope
            logger.warning(f"[ENGINE-V2] Entity scope detected: {entity_scope}")
        
        # v4.0: Also use scope_filter as entity_scope if provided
        if scope_filter and not entity_scope:
            # Format for SQL generator: needs semantic_type, value, hub_column
            analysis['entity_scope'] = {
                'semantic_type': scope_filter['dimension'],  # e.g., 'company'
                'value': scope_filter['value'],              # e.g., 'TISI'
                'hub_column': scope_filter['dimension'],     # try direct column match too
                'scope_column': scope_filter['dimension']    # original column name
            }
            logger.warning(f"[ENGINE-V2] Using scope as entity filter: {analysis['entity_scope']}")
        
        # =====================================================================
        # GATHER ALL FIVE TRUTHS - NO SKIPPING
        # =====================================================================
        # CRITICAL: Every question needs all truths for proper triangulation.
        # Validation questions ESPECIALLY need Regulatory + Reference to verify
        # whether Reality matches what SHOULD be configured.
        # =====================================================================
        
        # Truth 1: REALITY - What the data shows
        try:
            reality = self._gather_reality(question, analysis)
            logger.warning(f"[ENGINE-V2] REALITY gathered: {len(reality)} truths")
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in gather_reality: {e}")
            import traceback
            logger.error(f"[ENGINE-V2] Reality traceback: {traceback.format_exc()}")
            reality = []
        
        # Check for pending clarification from reality gathering
        if context.get('pending_clarification') or self._pending_clarification:
            clarification = context.get('pending_clarification') or self._pending_clarification
            self._pending_clarification = None
            return clarification
        
        # Truth 2: INTENT - What customer wants (SOWs, requirements)
        try:
            intent = self._gather_intent(question, analysis)
            logger.warning(f"[ENGINE-V2] INTENT gathered: {len(intent)} truths")
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in gather_intent: {e}")
            intent = []
        
        # Truth 3: CONFIGURATION - How system is configured (code tables)
        try:
            configuration = self._gather_configuration(question, analysis)
            logger.warning(f"[ENGINE-V2] CONFIGURATION gathered: {len(configuration)} truths")
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in gather_configuration: {e}")
            configuration = []
        
        # Truths 4, 5, 6: REFERENCE, REGULATORY, COMPLIANCE (global library)
        try:
            reference, regulatory, compliance = self._gather_reference_library(question, analysis)
            logger.warning(f"[ENGINE-V2] REFERENCE gathered: {len(reference)} truths")
            logger.warning(f"[ENGINE-V2] REGULATORY gathered: {len(regulatory)} truths")
            logger.warning(f"[ENGINE-V2] COMPLIANCE gathered: {len(compliance)} truths")
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in gather_reference_library: {e}")
            reference, regulatory, compliance = [], [], []
        
        # Log total truths gathered
        total_truths = len(reality) + len(intent) + len(configuration) + len(reference) + len(regulatory) + len(compliance)
        logger.warning(f"[ENGINE-V2] TOTAL TRUTHS GATHERED: {total_truths}")
        
        # Enrich semantic truths with LLM extraction (LLM Lookups)
        if self.truth_enricher:
            intent = self.truth_enricher.enrich_batch(intent)
            reference = self.truth_enricher.enrich_batch(reference)
            regulatory = self.truth_enricher.enrich_batch(regulatory)
            compliance = self.truth_enricher.enrich_batch(compliance)
            # Configuration is DuckDB (structured), light enrichment
            configuration = self.truth_enricher.enrich_batch(configuration)
        
        # Detect conflicts between truths
        conflicts = self._detect_conflicts(
            reality, intent, configuration, reference, regulatory, compliance
        )
        
        # Run proactive checks
        insights = self._run_proactive_checks(analysis)
        
        # Compliance check
        compliance_check = None
        if regulatory:
            compliance_check = self._check_compliance(reality, configuration, regulatory)
        
        # v3.0: Get Context Graph for synthesis
        context_graph = None
        if self.table_selector and hasattr(self.table_selector, '_get_context_graph'):
            try:
                context_graph = self.table_selector._get_context_graph()
            except Exception as e:
                logger.debug(f"[ENGINE-V2] Could not get context graph: {e}")
        
        # v3.2: Get entity gaps from Entity Registry (configured but not in docs, or vice versa)
        entity_gaps = []
        try:
            from backend.utils.entity_registry import get_entity_registry
            registry = get_entity_registry()
            if registry:
                entity_gaps = registry.get_gaps() or []
                if entity_gaps:
                    logger.warning(f"[ENGINE-V2] Found {len(entity_gaps)} entity gaps for gap detection")
        except Exception as e:
            logger.debug(f"[ENGINE-V2] Could not get entity gaps: {e}")
        
        # v4.5: Get organizational metrics from ProjectIntelligence
        organizational_metrics = []
        try:
            if PROJECT_INTELLIGENCE_AVAILABLE and get_project_intelligence and self.structured_handler:
                intelligence = get_project_intelligence(self.project, self.structured_handler)
                if intelligence:
                    organizational_metrics = intelligence.get_organizational_metrics()
                    if organizational_metrics:
                        logger.warning(f"[ENGINE-V2] Loaded {len(organizational_metrics)} organizational metrics")
        except Exception as e:
            logger.debug(f"[ENGINE-V2] Could not get organizational metrics: {e}")
        
        # Merge analysis flags into context for synthesizer
        synth_context = context.copy() if context else {}
        synth_context['is_config'] = analysis.get('is_config', False)
        synth_context['is_validation'] = analysis.get('is_validation', False)
        synth_context['is_employee_question'] = analysis.get('is_employee_question', False)
        synth_context['entity_gaps'] = entity_gaps  # v3.2: Pass gaps for synthesis
        synth_context['project'] = self.project  # v4.4: Pass project for usage analysis
        synth_context['organizational_metrics'] = organizational_metrics  # v4.5: Pre-computed org metrics
        
        # Synthesize answer
        try:
            answer = self.synthesizer.synthesize(
                question=question,
                mode=mode,
                reality=reality,
                intent=intent,
                configuration=configuration,
                reference=reference,
                regulatory=regulatory,
                compliance=compliance,
                conflicts=conflicts,
                insights=insights,
                compliance_check=compliance_check,
                context=synth_context,
                context_graph=context_graph  # v3.0
            )
        except Exception as e:
            logger.error(f"[ENGINE-V2] Error in synthesize: {e}")
            import traceback
            logger.error(f"[ENGINE-V2] Synthesize traceback: {traceback.format_exc()}")
            raise
        
        # Track SQL
        if self.reality_gatherer:
            self.last_executed_sql = self.reality_gatherer.last_executed_sql
            answer.executed_sql = self.last_executed_sql
        
        # v3.2: Attach consultative metadata (excel_spec, proactive_offers, etc.)
        if self.synthesizer and hasattr(self.synthesizer, 'get_consultative_metadata'):
            consultative_meta = self.synthesizer.get_consultative_metadata()
            if consultative_meta:
                answer.consultative_metadata = consultative_meta
                logger.warning(f"[ENGINE-V2] Consultative metadata: type={consultative_meta.get('question_type')}, "
                             f"offers={len(consultative_meta.get('proactive_offers', []))}")
        
        # Update history
        self.conversation_history.append({
            'question': question,
            'mode': mode.value if mode else 'search',
            'answer_length': len(answer.answer),
            'confidence': answer.confidence,
            'truths_gathered': {
                'reality': len(reality),
                'intent': len(intent),
                'configuration': len(configuration),
                'reference': len(reference),
                'regulatory': len(regulatory),
                'compliance': len(compliance)
            }
        })
        
        total_truths = len(reality) + len(intent) + len(configuration) + len(reference) + len(regulatory) + len(compliance)
        logger.info(f"[ENGINE-V2] Answer: {len(answer.answer)} chars, "
                   f"confidence={answer.confidence:.0%}, truths={total_truths}")
        
        return answer
    
    # =========================================================================
    # QUESTION ANALYSIS
    # =========================================================================
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect intelligence mode from question."""
        if any(w in q_lower for w in ['correct', 'valid', 'check', 'verify', 'audit']):
            return IntelligenceMode.VALIDATE
        if any(w in q_lower for w in ['compare', 'versus', 'vs', 'difference']):
            return IntelligenceMode.COMPARE
        if any(w in q_lower for w in ['how to', 'configure', 'setup', 'set up']):
            return IntelligenceMode.CONFIGURE
        if any(w in q_lower for w in ['report', 'summary', 'overview']):
            return IntelligenceMode.REPORT
        if any(w in q_lower for w in ['count', 'how many', 'total', 'sum']):
            return IntelligenceMode.ANALYZE
        return IntelligenceMode.SEARCH
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect relevant domains from question."""
        domains = []
        
        domain_keywords = {
            'payroll': ['payroll', 'pay', 'wage', 'salary', 'compensation'],
            'tax': ['tax', 'sui', 'suta', 'futa', 'withholding', 'w2', 'fica'],
            'benefits': ['benefit', 'deduction', '401k', 'insurance', 'health'],
            'time': ['time', 'hours', 'attendance', 'schedule', 'pto'],
            'hr': ['employee', 'hire', 'termination', 'job', 'position'],
            'gl': ['gl', 'general ledger', 'account', 'mapping'],
            'earnings': ['earnings', 'earning', 'pay code'],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in q_lower for kw in keywords):
                domains.append(domain)
        
        return domains or ['general']
    
    def _is_employee_question(self, q_lower: str) -> bool:
        """Check if question is about employee data."""
        return any(ind in q_lower for ind in self.EMPLOYEE_INDICATORS)
    
    def _is_validation_question(self, q_lower: str) -> bool:
        """Check if question is a validation/audit question."""
        return any(kw in q_lower for kw in self.VALIDATION_KEYWORDS)
    
    def _is_config_domain(self, q_lower: str) -> bool:
        """Check if question is about config (not employee data)."""
        return any(cd in q_lower for cd in self.CONFIG_DOMAINS)
    
    def _is_pure_chat_question(self, question: str, q_lower: str) -> bool:
        """
        Detect if this is a "Pure Chat" question - definitional/conceptual
        that doesn't require data gathering.
        
        Pure Chat = definitional patterns WITHOUT data indicators
        
        Examples that ARE Pure Chat:
        - "what is a benefit class?"
        - "how does UKG handle accruals?"
        - "explain garnishments"
        
        Examples that are NOT Pure Chat (need data):
        - "what is the headcount in Texas?" (has 'in Texas')
        - "what are our deduction codes?" (has 'our')
        - "how many employees have benefits?" (has 'how many')
        
        Returns:
            True if this is a pure definitional question
        """
        # Check for definitional patterns
        has_definitional_pattern = any(
            pattern in q_lower for pattern in self.PURE_CHAT_PATTERNS
        )
        
        if not has_definitional_pattern:
            return False
        
        # Check for data indicators that mean we need actual data
        has_data_indicator = any(
            indicator in q_lower for indicator in self.DATA_INDICATORS
        )
        
        if has_data_indicator:
            logger.warning(f"[PURE-CHAT] Definitional pattern found but has data indicator - NOT pure chat")
            return False
        
        logger.warning(f"[PURE-CHAT] Detected pure chat question: {question[:60]}...")
        return True
    
    def _has_deep_code_word(self, question: str) -> bool:
        """Check if question contains the code word to enable Claude fallback."""
        return self.PURE_CHAT_CODE_WORD.lower() in question.lower()
    
    def _detect_entity_scope(self, question: str, q_lower: str) -> Optional[Dict]:
        """
        Detect if question references specific entity values for scoping.
        
        Uses Context Graph to find hub values mentioned in the question.
        Returns scoping info that gatherers can use to filter queries.
        
        Example: "Show employees in company ABC" → scope to company_code='ABC'
        
        Returns:
            Dict with {semantic_type, value, hub_table, hub_column} or None
        """
        if not self.structured_handler or not self.table_selector:
            return None
        
        try:
            # Get Context Graph
            graph = self.table_selector._get_context_graph()
            if not graph or not graph.get('hubs'):
                return None
            
            # For each hub, check if any of its values appear in the question
            for hub in graph.get('hubs', []):
                hub_table = hub.get('table', '')
                hub_column = hub.get('column', '')
                semantic_type = hub.get('semantic_type', '')
                
                if not hub_table or not hub_column:
                    continue
                
                # Get distinct values from this hub
                try:
                    values = self.structured_handler.conn.execute(f"""
                        SELECT DISTINCT "{hub_column}" 
                        FROM "{hub_table}" 
                        WHERE "{hub_column}" IS NOT NULL
                        LIMIT 100
                    """).fetchall()
                    
                    for (val,) in values:
                        if not val:
                            continue
                        val_str = str(val).lower()
                        val_upper = str(val).upper()
                        
                        # Check if value appears in question (case-insensitive)
                        # Must be a "word" - not substring of another word
                        if len(val_str) >= 2:  # Skip single chars
                            # Match as word boundary
                            pattern = rf'\b{re.escape(val_str)}\b'
                            if re.search(pattern, q_lower):
                                logger.warning(f"[ENGINE-V2] Found entity scope: {semantic_type}={val}")
                                return {
                                    'semantic_type': semantic_type,
                                    'value': str(val),  # Original case
                                    'hub_table': hub_table,
                                    'hub_column': hub_column
                                }
                except Exception as e:
                    logger.debug(f"[ENGINE-V2] Could not check hub {hub_table}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"[ENGINE-V2] Entity scope detection failed: {e}")
        
        return None
    
    # =========================================================================
    # QUERY RESOLVER - Deterministic fast path for common queries
    # =========================================================================
    
    def _try_query_resolver(self, question: str) -> Optional[Dict]:
        """
        Try to resolve the query deterministically using QueryResolver.
        
        This does NOT short-circuit the pipeline. Instead, it returns
        resolution context that gets passed into the full gather flow,
        ensuring RealityGatherer uses the right table while still
        allowing Config/Reference/Regulatory gathering and triangulation.
        
        Returns:
            Dict with resolution context if resolved, None otherwise
        """
        if not self.structured_handler:
            return None
        
        try:
            from .query_resolver import QueryResolver
            
            logger.warning(f"[ENGINE-V2] Trying QueryResolver for: {question[:50]}...")
            resolver = QueryResolver(self.structured_handler)
            resolved = resolver.resolve(question, self.project)
            
            if resolved.success and resolved.sql:
                logger.warning(f"[ENGINE-V2] QueryResolver SUCCESS: {resolved.explanation}")
                logger.warning(f"[ENGINE-V2] Resolution path: {resolved.resolution_path}")
                logger.warning(f"[ENGINE-V2] SQL: {resolved.sql}")
                
                # Log reality context if present
                if resolved.reality_context:
                    breakdowns = resolved.reality_context.get('breakdowns', {})
                    logger.warning(f"[ENGINE-V2] Reality context: {len(breakdowns)} breakdowns gathered")
                
                # Return context for the full pipeline - don't short-circuit
                return {
                    'resolved': True,
                    'table_name': resolved.table_name,
                    'filter_column': resolved.filter_column,
                    'filter_values': resolved.filter_values,
                    'sql': resolved.sql,
                    'explanation': resolved.explanation,
                    'resolution_path': resolved.resolution_path,
                    'reality_context': resolved.reality_context,  # v2: Include breakdowns
                    'structured_output': resolved.structured_output,  # v3: Workforce snapshot etc.
                    'total_count': resolved.total_count  # v5: Real count for LIST queries
                }
            else:
                logger.warning(f"[ENGINE-V2] QueryResolver no match: {resolved.explanation or 'unknown'}")
                
        except Exception as e:
            logger.warning(f"[ENGINE-V2] QueryResolver error: {e}")
            import traceback
            logger.warning(f"[ENGINE-V2] Traceback: {traceback.format_exc()}")
        
        return None
    
    def _synthesize_with_resolver_context(
        self, 
        question: str, 
        resolver_context: Dict
    ) -> Optional[SynthesizedAnswer]:
        """
        CONSULTATIVE PATH: Synthesize answer using QueryResolver's structured output.
        
        This is called when QueryResolver already computed rich context like:
        - Workforce snapshots (active/termed/LOA by year)
        - Status breakdowns
        - Pre-computed metrics
        
        Instead of running a dumb COUNT(*), we pass this rich context to the LLM
        to generate a consultative response like a real consultant would give.
        
        Args:
            question: The user's question
            resolver_context: Dict from QueryResolver with structured_output
            
        Returns:
            SynthesizedAnswer with consultative response, or None to fall back
        """
        logger.warning("[CONSULTATIVE] Entering consultative synthesis path")
        
        structured_output = resolver_context.get('structured_output', {})
        if not structured_output:
            logger.warning("[CONSULTATIVE] No structured_output - falling back")
            return None
        
        # Get LLM orchestrator (through ConsultativeSynthesizer or direct)
        orchestrator = None
        if self._llm_synthesizer and hasattr(self._llm_synthesizer, '_orchestrator'):
            orchestrator = self._llm_synthesizer._orchestrator
        
        if not orchestrator:
            # Try to create one directly
            try:
                from utils.llm_orchestrator import LLMOrchestrator
                orchestrator = LLMOrchestrator()
                logger.warning("[CONSULTATIVE] Created new LLMOrchestrator")
            except Exception as e:
                logger.warning(f"[CONSULTATIVE] Could not create LLMOrchestrator: {e}")
                return None
        
        try:
            # Extract workforce snapshot data
            # Structure is: {'type': 'workforce_snapshot', 'years': {2024: {...}, ...}}
            snapshot = structured_output.get('years', {})
            current_year = max(snapshot.keys()) if snapshot else None
            
            if not current_year:
                logger.warning(f"[CONSULTATIVE] No years in snapshot - keys: {list(structured_output.keys())}")
                return None
            
            current = snapshot.get(current_year, {})
            active = current.get('active', 0)
            termed = current.get('termed', 0)
            loa = current.get('loa', 0)
            total = current.get('total', 0)
            
            # Build context for LLM
            context_parts = []
            
            # Current workforce status
            context_parts.append(f"CURRENT WORKFORCE ({current_year}):")
            context_parts.append(f"- Active employees: {active:,}")
            if loa > 0:
                context_parts.append(f"- On Leave of Absence: {loa:,}")
            if termed > 0:
                context_parts.append(f"- Terminated this year: {termed:,}")
            context_parts.append(f"- Total records in system: {total:,}")
            
            # Historical context
            if len(snapshot) > 1:
                context_parts.append(f"\nHISTORICAL TREND:")
                for year in sorted(snapshot.keys()):
                    if year != current_year:
                        yr_data = snapshot[year]
                        context_parts.append(
                            f"- {year}: {yr_data.get('active', 0):,} active, "
                            f"{yr_data.get('termed', 0):,} terminated"
                        )
            
            # Reality context (breakdowns if available)
            reality_context = resolver_context.get('reality_context') or {}
            breakdowns = reality_context.get('breakdowns', {}) if reality_context else {}
            if breakdowns:
                context_parts.append(f"\nAVAILABLE BREAKDOWNS:")
                for dim, values in list(breakdowns.items())[:3]:
                    top_values = list(values.items())[:5]
                    if top_values:
                        formatted = ', '.join(f'{k}: {v}' for k, v in top_values)
                        context_parts.append(f"- By {dim}: {formatted}")
            
            context_text = "\n".join(context_parts)
            
            # Build the consultant prompt
            expert_prompt = """You are a senior HCM implementation consultant answering a client's question.

YOUR RESPONSE MUST:
1. Lead with the direct answer (the key number they asked for)
2. Add context a consultant would highlight (current vs historical, composition)
3. Offer 1-2 relevant follow-up analyses

STYLE:
- Conversational but professional
- Lead with the answer, not preamble
- Interpret the data, don't just list it
- Like a consultant who knows this client

EXAMPLE:
Question: "How many employees?"
Good: "You have 3,976 active employees currently. There are also 36 on leave of absence. 
Your workforce has been relatively stable - down slightly from 4,012 active last year.
Want me to break this down by department or location?"

Bad: "Based on the data, I found 3,976 active records and 36 LOA records totaling..."
"""
            
            logger.warning(f"[CONSULTATIVE] Calling LLM with {len(context_text)} chars of context")
            
            # Call LLM orchestrator
            result = orchestrator.synthesize_answer(
                question=question,
                context=context_text,
                expert_prompt=expert_prompt,
                use_claude_fallback=True
            )
            
            if result.get('success') and result.get('response'):
                response_text = result['response']
                model_used = result.get('model_used', 'unknown')
                
                if len(response_text) > 50:
                    # Build the SynthesizedAnswer
                    answer = SynthesizedAnswer(
                        question=question,
                        answer=response_text,
                        confidence=0.9,
                        from_reality=[
                            Truth(
                                source_type='reality',
                                source_name=resolver_context.get('table_name', 'workforce'),
                                content=structured_output,
                                confidence=0.95,
                                location='QueryResolver',
                                metadata={'consultative': True, 'model': model_used}
                            )
                        ],
                        reasoning=[
                            f"Used QueryResolver workforce snapshot → LLM synthesis ({model_used})",
                            f"Current year ({current_year}): {active:,} active, {loa:,} LOA, {termed:,} termed",
                            resolver_context.get('explanation', ''),
                        ],
                        structured_output={
                            'type': 'workforce_snapshot',
                            'snapshot': snapshot,
                            'sql': resolver_context.get('sql', ''),
                            'synthesis_model': model_used
                        }
                    )
                    
                    logger.warning(f"[CONSULTATIVE] SUCCESS via {model_used} ({len(response_text)} chars)")
                    return answer
                else:
                    logger.warning(f"[CONSULTATIVE] Response too short ({len(response_text)} chars)")
            else:
                logger.warning(f"[CONSULTATIVE] LLM failed: {result.get('error', 'unknown')}")
            
            return None
                
        except Exception as e:
            logger.error(f"[CONSULTATIVE] Error in synthesis: {e}")
            import traceback
            logger.error(f"[CONSULTATIVE] Traceback: {traceback.format_exc()}")
            return None
    
    def _handle_pure_chat(self, question: str, q_lower: str) -> Optional[SynthesizedAnswer]:
        """
        Handle Pure Chat questions - definitional/conceptual questions
        that don't need Reality/Configuration data gathering.
        
        Flow:
        1. Search ChromaDB for Reference documentation
        2. Build context from Reference truths
        3. Call LOCAL LLM (Mistral) for synthesis
        4. Only use Claude API if [ASTROS2X] code word is present
        
        Args:
            question: User's question
            q_lower: Lowercase version
            
        Returns:
            SynthesizedAnswer or None if Pure Chat fails
        """
        logger.warning(f"[PURE-CHAT] Handling: {question[:60]}...")
        
        # Check for code word that enables Claude fallback
        use_claude_fallback = self._has_deep_code_word(question)
        if use_claude_fallback:
            logger.warning(f"[PURE-CHAT] Code word '{self.PURE_CHAT_CODE_WORD}' detected - Claude fallback ENABLED")
            # Remove code word from question for cleaner processing
            clean_question = question.replace(self.PURE_CHAT_CODE_WORD, '').replace(self.PURE_CHAT_CODE_WORD.lower(), '').strip()
        else:
            logger.warning(f"[PURE-CHAT] No code word - LOCAL LLM ONLY (no Claude fallback)")
            clean_question = question
        
        # Step 1: Gather Reference truths from ChromaDB
        reference_truths = []
        try:
            if self.reference_gatherer:
                reference_truths = self.reference_gatherer.gather(
                    clean_question, 
                    {'system': self.product_id or 'ukg'}
                )
                logger.warning(f"[PURE-CHAT] Got {len(reference_truths)} Reference truths")
            else:
                logger.warning("[PURE-CHAT] No reference_gatherer available")
        except Exception as e:
            logger.error(f"[PURE-CHAT] Reference gathering error: {e}")
        
        # Also try Regulatory truths for compliance-related questions
        regulatory_truths = []
        compliance_keywords = ['compliance', 'regulation', 'law', 'legal', 'irs', 'dol', 'flsa', 'aca', 'cobra']
        if any(kw in q_lower for kw in compliance_keywords):
            try:
                if self.regulatory_gatherer:
                    regulatory_truths = self.regulatory_gatherer.gather(
                        clean_question,
                        {'system': self.product_id or 'ukg'}
                    )
                    logger.warning(f"[PURE-CHAT] Got {len(regulatory_truths)} Regulatory truths")
            except Exception as e:
                logger.error(f"[PURE-CHAT] Regulatory gathering error: {e}")
        
        # Step 2: Build context from truths
        context_parts = []
        
        if reference_truths:
            context_parts.append("REFERENCE DOCUMENTATION:")
            for i, truth in enumerate(reference_truths[:5], 1):
                content = truth.content
                if isinstance(content, dict):
                    text = content.get('text', str(content))
                    source = content.get('metadata', {}).get('filename', 'Reference')
                else:
                    text = str(content)
                    source = 'Reference'
                context_parts.append(f"\n[{i}] From {source}:\n{text[:1500]}")
        
        if regulatory_truths:
            context_parts.append("\n\nREGULATORY CONTEXT:")
            for i, truth in enumerate(regulatory_truths[:3], 1):
                content = truth.content
                if isinstance(content, dict):
                    text = content.get('text', str(content))
                else:
                    text = str(content)
                context_parts.append(f"\n[{i}] {text[:1000]}")
        
        context_text = "\n".join(context_parts)
        
        # If no reference context found, provide a helpful base response
        if not context_text.strip():
            logger.warning("[PURE-CHAT] No Reference/Regulatory context found")
            context_text = """No specific documentation found in the knowledge base for this topic.
Please provide a general explanation based on common HCM/HR practices."""
        
        # Step 3: Get LLM orchestrator
        orchestrator = None
        if self._llm_synthesizer and hasattr(self._llm_synthesizer, '_orchestrator'):
            orchestrator = self._llm_synthesizer._orchestrator
        
        if not orchestrator:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
                orchestrator = LLMOrchestrator()
                logger.warning("[PURE-CHAT] Created new LLMOrchestrator")
            except Exception as e:
                logger.error(f"[PURE-CHAT] Could not create LLMOrchestrator: {e}")
                return None
        
        # Step 4: Build expert prompt for definitional questions
        expert_prompt = """You are an expert HCM implementation consultant answering a conceptual question.

YOUR TASK: Provide a clear, educational explanation of the concept asked about.

USE THE PROVIDED DOCUMENTATION to ground your answer in specific system knowledge.
If documentation is available, reference specific features, settings, or best practices from it.

STYLE:
- Start with a direct definition or explanation
- Use concrete examples to illustrate concepts
- Explain WHY this matters in an implementation context
- Keep it conversational but professional
- 2-4 paragraphs is ideal

DO NOT:
- Say "based on the documentation provided"
- Start with "As an AI..." or similar
- Give overly generic answers when specific docs are available"""

        logger.warning(f"[PURE-CHAT] Calling LLM with {len(context_text)} chars of context")
        
        # Step 5: Call LLM - LOCAL ONLY unless code word present
        try:
            result = orchestrator.synthesize_answer(
                question=clean_question,
                context=context_text,
                expert_prompt=expert_prompt,
                use_claude_fallback=use_claude_fallback  # Only True if [ASTROS2X] present
            )
            
            if result.get('success') and result.get('response'):
                response_text = result['response']
                model_used = result.get('model_used', 'local')
                
                if len(response_text) > 50:
                    # Build SynthesizedAnswer
                    answer = SynthesizedAnswer(
                        question=question,
                        answer=response_text,
                        confidence=0.85,
                        from_reference=reference_truths[:3],
                        from_regulatory=regulatory_truths[:2] if regulatory_truths else [],
                        reasoning=[
                            f"Pure Chat path - definitional question",
                            f"Synthesized via {model_used}",
                            f"Reference docs: {len(reference_truths)}",
                        ],
                        structured_output={
                            'type': 'pure_chat',
                            'model': model_used,
                            'reference_count': len(reference_truths),
                            'regulatory_count': len(regulatory_truths),
                            'claude_enabled': use_claude_fallback
                        }
                    )
                    
                    logger.warning(f"[PURE-CHAT] SUCCESS via {model_used} ({len(response_text)} chars)")
                    return answer
                else:
                    logger.warning(f"[PURE-CHAT] Response too short ({len(response_text)} chars)")
            else:
                logger.warning(f"[PURE-CHAT] LLM failed: {result.get('error', 'unknown')}")
                
        except Exception as e:
            logger.error(f"[PURE-CHAT] Synthesis error: {e}")
            import traceback
            logger.error(f"[PURE-CHAT] Traceback: {traceback.format_exc()}")
        
        return None
    
    def _try_deterministic_path(self, question: str) -> Optional[SynthesizedAnswer]:
        """
        PRIMARY PATH: Try to answer using Term Index + SQL Assembler.
        
        NO LLM. NO SCORING. JUST LOOKUP + ASSEMBLY + EXECUTE.
        
        This short-circuits the old flow if successful, returning
        a complete SynthesizedAnswer with data.
        
        EVOLUTION 10: No more None returns that trigger garbage fallback.
        Now returns structured failure responses:
        - CANNOT_RESOLVE - We don't understand the terms  
        - NEEDS_CLARIFICATION - Ambiguous query
        - NO_DATA - Understood but found nothing
        - COMPLEX_QUERY - Needs full pipeline (Reference/Regulatory)
        - SYSTEM_ERROR - Technical failure
        
        Returns:
            SynthesizedAnswer - either with data OR with honest failure info
        """
        logger.warning(f"[DETERMINISTIC] Entering deterministic path. Available={DETERMINISTIC_PATH_AVAILABLE}")
        
        if not DETERMINISTIC_PATH_AVAILABLE:
            logger.warning("[DETERMINISTIC] Path not available - missing imports")
            return build_system_error_response(
                question=question,
                error="Deterministic path components not available (TermIndex/SQLAssembler)",
                component="deterministic_path_imports"
            )
        
        if not self.structured_handler:
            logger.warning("[DETERMINISTIC] No structured handler available")
            return build_system_error_response(
                question=question,
                error="No database connection available. Please upload data first.",
                component="structured_handler"
            )
        
        try:
            # Step 1: Parse intent from question
            parsed = parse_intent(question)
            logger.warning(f"[DETERMINISTIC] Parsed: intent={parsed.intent.value}, domain={parsed.domain.value}")
            
            # Skip deterministic path for complex analysis questions
            # These need Reference/Regulatory/Compliance from ChromaDB
            q_lower = question.lower()
            complex_indicators = [
                'why', 'explain', 'analyze', 'recommend', 'should',
                'compliant', 'compliance', 'regulatory', 'risk',
                'best practice', 'validate', 'correct', 'wrong'
            ]
            matched_indicators = [ind for ind in complex_indicators if ind in q_lower]
            if matched_indicators:
                logger.warning(f"[DETERMINISTIC] Complex question detected ({matched_indicators}) - deferring to full pipeline")
                # Return COMPLEX_QUERY status so engine knows to continue with full pipeline
                return build_complex_query_response(
                    question=question,
                    reason=f"Question contains analysis keywords: {matched_indicators}",
                    required_sources=['reference', 'regulatory', 'compliance'],
                    context={'matched_indicators': matched_indicators}
                )
            
            # ================================================================
            # EVOLUTION 10: MULTI-HOP RELATIONSHIP DETECTION
            # Check for possessive patterns ("manager's department") and
            # relationship keywords ("reports to", "in John's team")
            # ================================================================
            if RELATIONSHIP_RESOLVER_AVAILABLE:
                multi_hop_info = detect_multi_hop_query(question)
                if multi_hop_info:
                    logger.warning(f"[DETERMINISTIC] Multi-hop pattern detected: {multi_hop_info}")
                    
                    # Try to handle multi-hop query
                    multi_hop_result = self._try_multi_hop_query(question, multi_hop_info)
                    if multi_hop_result:
                        return multi_hop_result
                    # If multi-hop fails, fall through to regular path
                    logger.warning("[DETERMINISTIC] Multi-hop query failed, trying regular path")
            
            # Step 2: Resolve terms using Term Index (EVOLUTION 3: with numeric support)
            logger.warning(f"[DETERMINISTIC] Creating TermIndex with project='{self.project}'")
            term_index = TermIndex(self.structured_handler.conn, self.project)
            
            # Tokenize question - but also keep numeric phrases intact
            words = [w.strip().lower() for w in re.split(r'\s+', question) if w.strip()]
            
            # EVOLUTION 3: Also extract potential numeric expressions as phrases
            # Patterns like "above 50000", "between 20 and 40", "at least 100k"
            numeric_phrase_patterns = [
                r'(?:above|over|more than|greater than|exceeds?)\s+[\$]?\d[\d,]*[kKmM]?',
                r'(?:below|under|less than)\s+[\$]?\d[\d,]*[kKmM]?',
                r'(?:at least|minimum|min)\s+[\$]?\d[\d,]*[kKmM]?',
                r'(?:at most|maximum|max)\s+[\$]?\d[\d,]*[kKmM]?',
                r'between\s+[\$]?\d[\d,]*[kKmM]?\s+and\s+[\$]?\d[\d,]*[kKmM]?',
            ]
            
            numeric_phrases = []
            for pattern in numeric_phrase_patterns:
                matches = re.findall(pattern, question.lower())
                numeric_phrases.extend(matches)
            
            # EVOLUTION 4: Extract date phrases
            # Patterns like "hired last year", "in 2024", "hired in Q4"
            date_phrase_patterns = [
                # Action + temporal: "hired last year", "terminated this month"
                r'(?:hired|terminated|started|ended|born)\s+(?:last|this|next)\s+(?:year|month|quarter|week)',
                r'(?:hired|terminated|started|ended|born)\s+(?:in|during)\s+(?:20\d{2})',
                r'(?:hired|terminated|started|ended|born)\s+(?:in|during)\s+q[1-4](?:\s+20\d{2})?',
                # Standalone temporal (lower priority, less context)
                r'(?:last|this|next)\s+(?:year|month|quarter|week)',
                r'(?:in|during)\s+(?:20\d{2})',
                r'(?:in|during)\s+q[1-4](?:\s+20\d{2})?',
                r'(?:in|during)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+20\d{2})?',
                r'(?:before|after|since)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+20\d{2})?',
                r'(?:before|after|since)\s+(?:20\d{2})',
            ]
            
            date_phrases = []
            for pattern in date_phrase_patterns:
                matches = re.findall(pattern, question.lower())
                date_phrases.extend(matches)
            
            # EVOLUTION 5: Extract OR phrases
            # Pattern: "X or Y" where X and Y are words
            or_pattern = r'(\w+)\s+or\s+(\w+)'
            or_matches = re.findall(or_pattern, question.lower())
            or_phrases = [f"{m[0]} or {m[1]}" for m in or_matches]
            
            # EVOLUTION 6: Extract negation phrases
            # Patterns: "not X", "not in X", "excluding X", "except X", "without X"
            # Order matters - more specific patterns first, and track what's matched
            negation_phrases = []
            matched_positions = set()
            
            # First: "not in X" pattern (most specific)
            for match in re.finditer(r'not\s+in\s+(\w+)', question.lower()):
                term = match.group(1)
                negation_phrases.append(f"not {term}")
                matched_positions.add(match.start())
            
            # Second: "not X" but NOT "not in" (avoid double-matching)
            for match in re.finditer(r'not\s+(\w+)', question.lower()):
                if match.start() not in matched_positions:
                    term = match.group(1)
                    if term != 'in':  # Skip "not in" when it's part of "not in X"
                        negation_phrases.append(f"not {term}")
            
            # Other negation keywords
            for pattern in [r'excluding\s+(\w+)', r'except\s+(\w+)', r'without\s+(\w+)']:
                for match in re.finditer(pattern, question.lower()):
                    negation_phrases.append(f"not {match.group(1)}")
            
            # EVOLUTION 7: Detect aggregation intent EARLY and exclude keywords from term resolution
            # These words are OPERATORS, not filter values
            AGG_KEYWORDS = {'average', 'avg', 'mean', 'sum', 'total', 'minimum', 'min', 'maximum', 'max', 'count', 'headcount', 'number'}
            
            # Also detect the aggregation target (the noun after the aggregation keyword)
            agg_target_word = None
            agg_patterns = [
                (r'(?:average|avg|mean)\s+(\w+)', 'average'),
                (r'(?:minimum|min|lowest|smallest)\s+(\w+)', 'minimum'),
                (r'(?:maximum|max|highest|largest|biggest)\s+(\w+)', 'maximum'),
                (r'(?:total|sum|sum of)\s+(\w+)', 'sum'),
            ]
            for pattern, _ in agg_patterns:
                match = re.search(pattern, question.lower())
                if match:
                    agg_target_word = match.group(1)
                    logger.warning(f"[DETERMINISTIC] Early aggregation detection: target word='{agg_target_word}'")
                    break
            
            # Filter out words that are part of phrases to avoid duplicate/conflicting matches
            phrase_words = set()
            if numeric_phrases:
                for phrase in numeric_phrases:
                    phrase_words.update(phrase.split())
            if date_phrases:
                for phrase in date_phrases:
                    phrase_words.update(phrase.split())
            if or_phrases:
                for phrase in or_phrases:
                    phrase_words.update(phrase.split())
            if negation_phrases:
                for phrase in negation_phrases:
                    phrase_words.update(phrase.split())
                # Also add the negation keywords themselves
                phrase_words.update(['not', 'in', 'excluding', 'except', 'without'])
            
            # Add aggregation keywords to phrase_words so they don't get resolved as filter values
            phrase_words.update(AGG_KEYWORDS)
            
            # Also add the aggregation target word - it's the COLUMN to aggregate, not a filter
            if agg_target_word:
                phrase_words.add(agg_target_word)
            
            # EVOLUTION 8: Detect GROUP BY dimension EARLY to exclude from term resolution
            # Patterns: "by state", "per department", "for each location", "broken down by region"
            # EVOLUTION 10 FIX: Also capture multi-word dimensions like "job code", "employee type"
            group_by_dimension = None
            group_by_patterns = [
                r'\bby\s+(\w+\s+\w+)',      # "by job code", "by employee type" (2 words first)
                r'\bby\s+(\w+)',            # "by state", "by department" (1 word fallback)
                r'\bper\s+(\w+\s+\w+)',     # "per pay period"
                r'\bper\s+(\w+)',           # "per location", "per employee"
                r'\bfor each\s+(\w+\s+\w+)', # "for each job code"
                r'\bfor each\s+(\w+)',      # "for each state"
                r'\bbroken down by\s+(\w+\s+\w+)', # "broken down by job code"
                r'\bbroken down by\s+(\w+)', # "broken down by region"
                r'\bgrouped by\s+(\w+\s+\w+)', # "grouped by job code"
                r'\bgrouped by\s+(\w+)',    # "grouped by status"
            ]
            for pattern in group_by_patterns:
                match = re.search(pattern, question.lower())
                if match:
                    group_by_dimension = match.group(1).strip()
                    # Exclude dimension words AND "by" from term resolution
                    for dim_word in group_by_dimension.split():
                        phrase_words.add(dim_word)
                    phrase_words.add('by')
                    phrase_words.add('per')
                    logger.warning(f"[DETERMINISTIC] Detected GROUP BY dimension: '{group_by_dimension}'")
                    break
            
            if phrase_words:
                words = [w for w in words if w not in phrase_words]
            
            # Combine words and all phrase types for resolution
            terms_to_resolve = words + numeric_phrases + date_phrases + or_phrases + negation_phrases
            
            # EVOLUTION 10 FIX: Add GROUP BY dimension to resolution so term_index finds the right table
            # Don't exclude it - resolve it! The infrastructure knows job_code → company table
            if group_by_dimension:
                # Add as underscore version for column matching
                group_by_term = group_by_dimension.replace(' ', '_')
                terms_to_resolve.append(group_by_term)
                logger.warning(f"[DETERMINISTIC] Added GROUP BY dimension to resolution: '{group_by_term}'")
            
            logger.warning(f"[DETERMINISTIC] Resolving terms: words={words}, numeric={numeric_phrases}, date={date_phrases}, or={or_phrases}, negation={negation_phrases}, group_by={group_by_dimension}")
            
            # Use enhanced resolution if available (includes numeric, date, OR, and negation parsing)
            if hasattr(term_index, 'resolve_terms_enhanced'):
                term_matches = term_index.resolve_terms_enhanced(terms_to_resolve, detect_numeric=True, detect_dates=True, detect_or=True, detect_negation=True, full_question=question)
            else:
                term_matches = term_index.resolve_terms(terms_to_resolve)
            
            # Step 3: Detect aggregation intent from question keywords BEFORE checking term_matches
            # EVOLUTION 7: Override parsed intent for aggregation queries
            question_lower = question.lower()
            detected_intent = None
            agg_target = None
            
            # EVOLUTION 8: First check for COUNT-style queries (headcount, count, how many)
            count_keywords = ['headcount', 'head count', 'count', 'how many', 'number of', 'total employees', 'total people']
            if any(kw in question_lower for kw in count_keywords):
                detected_intent = 'count'
                logger.warning(f"[DETERMINISTIC] Detected COUNT intent from keyword")
            
            # Aggregation keyword patterns with target extraction
            agg_patterns = [
                (r'(?:average|avg|mean)\s+(\w+)', 'average'),
                (r'(?:minimum|min|lowest|smallest)\s+(\w+)', 'minimum'),
                (r'(?:maximum|max|highest|largest|biggest)\s+(\w+)', 'maximum'),
                (r'(?:total|sum|sum of)\s+(\w+)', 'sum'),
            ]
            
            # Only check aggregation patterns if we didn't already detect COUNT
            if not detected_intent:
                for pattern, intent_type in agg_patterns:
                    match = re.search(pattern, question_lower)
                    if match:
                        detected_intent = intent_type
                        agg_target = match.group(1)
                        logger.warning(f"[DETERMINISTIC] Detected {intent_type.upper()} intent, target='{agg_target}'")
                        break
            
            # If aggregation detected, resolve the target to a numeric column
            agg_matches = []
            if detected_intent and agg_target:
                agg_matches = term_index.resolve_aggregation_target(agg_target, domain=parsed.domain.value)
                if agg_matches:
                    logger.warning(f"[DETERMINISTIC] Added {len(agg_matches)} aggregation target matches")
            
            # If no term matches and no aggregation matches, fall back to local LLM
            # This handles general questions that don't relate to loaded data
            # ALSO fall back if ALL matches are low-confidence "reasoned" matches (MetadataReasoner guesses)
            # BUT: Trust reasoned matches with operator='GROUP BY' - those are column name matches
            all_reasoned_low_conf = (
                term_matches and 
                all(getattr(m, 'term_type', '') == 'reasoned' for m in term_matches) and
                all(getattr(m, 'confidence', 1.0) < 0.8 for m in term_matches) and
                # NEW: Trust column name matches (GROUP BY) even if low confidence
                not any(getattr(m, 'operator', '') == 'GROUP BY' for m in term_matches)
            )
            
            if not term_matches and not agg_matches:
                logger.warning(f"[DETERMINISTIC] No term matches found - checking for Pure Chat fallback")
                should_fallback = True
            elif all_reasoned_low_conf:
                logger.warning(f"[DETERMINISTIC] All matches are low-confidence reasoned - checking for Pure Chat fallback")
                should_fallback = True
            else:
                should_fallback = False
            
            if should_fallback:
                # Check if this looks like a data question or a general question
                data_keywords = ['how many', 'count', 'list', 'show me', 'display', 'give me',
                                 'employees', 'workers', 'deductions', 'earnings', 'payroll',
                                 'in texas', 'in california', 'our ', 'my ', 'total', 'sum',
                                 'report', 'export', 'table']
                is_data_question = any(kw in question.lower() for kw in data_keywords)
                
                if is_data_question:
                    # This was a data question but we can't find the data
                    logger.warning(f"[DETERMINISTIC] Data question with no/weak matches - returning resolution failure")
                    return build_cannot_resolve_response(
                        question=question,
                        reason="Could not resolve any terms to database columns",
                        unresolved_terms=terms_to_resolve[:5],
                        suggestions=[],
                        available_columns=[],
                        context={
                            'parsed_intent': parsed.intent.value,
                            'group_by_dimension': group_by_dimension,
                            'terms_attempted': terms_to_resolve[:10]
                        }
                    )
                else:
                    # General question - route to local LLM (Pure Chat path)
                    logger.warning(f"[DETERMINISTIC] General question - routing to Pure Chat handler")
                    try:
                        pure_chat_result = self._handle_pure_chat(question, question.lower())
                        if pure_chat_result:
                            logger.warning(f"[DETERMINISTIC] Pure Chat fallback succeeded")
                            # Prepend transparency message
                            no_data_prefix = "**No data found that is relevant to your request**, but this is what was found when I queried the HCMPACT LLM:\n\n---\n\n"
                            pure_chat_result.answer = no_data_prefix + pure_chat_result.answer
                            pure_chat_result.reasoning.insert(0, "No matching data - fell back to local LLM")
                            return pure_chat_result
                    except Exception as e:
                        logger.error(f"[DETERMINISTIC] Pure Chat fallback failed: {e}")
                    
                    # If Pure Chat also fails, return honest failure
                    return build_cannot_resolve_response(
                        question=question,
                        reason="Could not resolve any terms to database columns",
                        unresolved_terms=terms_to_resolve[:5],
                        suggestions=[],
                        available_columns=[],
                        context={
                            'parsed_intent': parsed.intent.value,
                            'group_by_dimension': group_by_dimension,
                            'terms_attempted': terms_to_resolve[:10]
                        }
                    )
            
            # If GROUP BY detected but no explicit count intent, set it
            if group_by_dimension and not detected_intent:
                detected_intent = 'count'
                logger.warning(f"[DETERMINISTIC] GROUP BY detected - treating as COUNT query")
            
            # Merge term_matches and agg_matches
            if agg_matches:
                term_matches = term_matches + agg_matches
            
            logger.warning(f"[DETERMINISTIC] Found {len(term_matches)} total term matches")
            for match in term_matches:
                logger.warning(f"[DETERMINISTIC]   - {match.term} → {match.table_name}.{match.column_name} {match.operator} '{match.match_value}'")
            
            # Step 4: Map parsed intent to assembler intent
            intent_map = {
                'count': AssemblerIntent.COUNT,
                'list': AssemblerIntent.LIST,
                'sum': AssemblerIntent.SUM,
                'average': AssemblerIntent.AVERAGE,
                'minimum': AssemblerIntent.MINIMUM,
                'maximum': AssemblerIntent.MAXIMUM,
                'compare': AssemblerIntent.COMPARE,
            }
            
            # Use detected aggregation intent if found, otherwise use parsed intent
            if detected_intent:
                assembler_intent = intent_map.get(detected_intent, AssemblerIntent.LIST)
            else:
                assembler_intent = intent_map.get(parsed.intent.value, AssemblerIntent.LIST)
            
            # Step 4: Resolve GROUP BY dimension to a column if detected
            # EVOLUTION 8 FIX: Use concept terms from term_index instead of hardcoded synonyms
            # EVOLUTION 10 FIX: Strongly deprioritize config/validation tables for GROUP BY
            group_by_column = None
            if group_by_dimension:
                # Try each variant until we find usable CONCEPT/COLUMN matches
                # Prefer underscore variant first (how columns are typically named)
                # Skip "reasoned" matches - those are just text content guesses
                dim_variants_ordered = [
                    group_by_dimension.replace(' ', '_'),  # "job_code" first
                    group_by_dimension,                     # "job code" second
                    group_by_dimension.replace('_', ' '),   # Reverse if needed
                ]
                # Remove duplicates while preserving order
                dim_variants_ordered = list(dict.fromkeys(dim_variants_ordered))
                
                dim_matches = []
                column_matches = []
                for variant in dim_variants_ordered:
                    dim_matches = term_index.resolve_terms([variant])
                    if dim_matches:
                        # Filter for COLUMN-IDENTIFYING match types:
                        # 1. concept = explicit vocabulary mapping to column
                        # 2. synonym = synonym that maps to column  
                        # 3. reasoned with operator='GROUP BY' = MetadataReasoner found column name match
                        # EXCLUDE: value (row data), numeric, pattern, reasoned text searches (ILIKE)
                        
                        def is_column_identifying_match(m) -> bool:
                            """Check if this match identifies a column (not a text search)."""
                            if not m.column_name or not m.table_name:
                                return False
                            # Explicit column types from term_index
                            if m.term_type in {'concept', 'synonym'}:
                                return True
                            # MetadataReasoner column name match (operator='GROUP BY')
                            if m.term_type == 'reasoned' and m.operator == 'GROUP BY':
                                return True
                            return False
                        
                        column_matches = [m for m in dim_matches if is_column_identifying_match(m)]
                        
                        logger.warning(f"[DETERMINISTIC] GROUP BY variant '{variant}': {len(dim_matches)} total, {len(column_matches)} column-identifying matches")
                        
                        # If no quality matches, also try matches where column name contains the search term
                        if not column_matches:
                            # Check if any match has the dimension word in the column name
                            dim_words = variant.replace('_', ' ').split()
                            column_matches = [m for m in dim_matches 
                                             if m.column_name and m.table_name
                                             and any(w in m.column_name.lower() for w in dim_words)]
                            if column_matches:
                                logger.warning(f"[DETERMINISTIC] Found {len(column_matches)} matches via column name pattern")
                        
                        if column_matches:
                            break  # Found usable matches
                
                # Debug logging - show what we found
                if dim_matches:
                    type_counts = {}
                    for m in dim_matches:
                        type_counts[m.term_type] = type_counts.get(m.term_type, 0) + 1
                    logger.warning(f"[DETERMINISTIC] dim_matches: {len(dim_matches)} total, types: {type_counts}, usable: {len(column_matches)}")
                    for m in dim_matches[:3]:
                        logger.warning(f"[DETERMINISTIC]   - type={m.term_type}, table='{m.table_name[-35:] if m.table_name else 'None'}', col='{m.column_name}'")
                
                if column_matches:
                    # EVOLUTION 10 FIX: Multi-tier preference for GROUP BY column selection
                    # Tier 1: Reality/employee tables (NOT config/validation)
                    # Tier 2: Any non-config/validation table
                    # Tier 3: Config tables (last resort)
                    
                    def is_config_table(table_name: str) -> bool:
                        """Check if table is a config/validation/lookup table."""
                        t = table_name.lower()
                        return 'config' in t or 'validation' in t or 'lookup' in t or '_ref_' in t
                    
                    def is_employee_table(table_name: str, entity: str) -> bool:
                        """Check if table contains employee data."""
                        t = table_name.lower()
                        return (entity == 'employee' or 
                                'employee' in t or 
                                'personal' in t or
                                '_us_1_' in t or  # Employee conversion tables
                                '_earnings' in t or
                                '_deductions' in t)
                    
                    # Tier 1: Employee/reality tables that are NOT config
                    tier1_matches = [m for m in column_matches 
                                     if is_employee_table(m.table_name, m.entity) 
                                     and not is_config_table(m.table_name)]
                    
                    # Tier 2: Any non-config table
                    tier2_matches = [m for m in column_matches 
                                     if not is_config_table(m.table_name)]
                    
                    # Tier 3: Config tables (avoid if possible)
                    tier3_matches = column_matches
                    
                    if tier1_matches:
                        best_match = tier1_matches[0]
                        logger.warning(f"[DETERMINISTIC] GROUP BY from TIER 1 (employee/reality): {best_match.table_name}")
                    elif tier2_matches:
                        best_match = tier2_matches[0]
                        logger.warning(f"[DETERMINISTIC] GROUP BY from TIER 2 (non-config): {best_match.table_name}")
                    else:
                        best_match = tier3_matches[0]
                        logger.warning(f"[DETERMINISTIC] GROUP BY from TIER 3 (config fallback): {best_match.table_name}")
                    
                    group_by_column = f"{best_match.table_name}.{best_match.column_name}"
                    logger.warning(f"[DETERMINISTIC] GROUP BY from concept: '{group_by_dimension}' → {group_by_column} (source={best_match.source})")
                    
                    # EVOLUTION 10 FIX: Add the GROUP BY match to term_matches
                    # This ensures the assembler uses the table with the GROUP BY column
                    # instead of the entity fallback table (which may not have this column)
                    term_matches = [best_match] + term_matches
                    logger.warning(f"[DETERMINISTIC] Added GROUP BY table to term_matches: {best_match.table_name}")
                
                # Fallback to hardcoded synonyms for common cases
                elif not group_by_column:
                    # EVOLUTION 11: Check _term_mappings for lookup mappings first
                    try:
                        lookup_mapping = term_index.conn.execute("""
                            SELECT lookup_table, lookup_display_column
                            FROM _term_mappings
                            WHERE project = ?
                            AND mapping_type = 'lookup'
                            AND LOWER(term) = LOWER(?)
                            LIMIT 1
                        """, [term_index.project, group_by_dimension]).fetchone()
                        
                        if lookup_mapping:
                            lookup_table, lookup_display = lookup_mapping
                            group_by_column = f"{lookup_table}.{lookup_display}"
                            logger.warning(f"[DETERMINISTIC] GROUP BY from lookup mapping: '{group_by_dimension}' → {group_by_column}")
                            
                            # Add synthetic match to ensure the lookup table is joined
                            from backend.utils.intelligence.term_index import TermMatch
                            synthetic_match = TermMatch(
                                term=group_by_dimension,
                                table_name=lookup_table,
                                column_name=lookup_display,
                                operator='GROUP BY',
                                match_value='',
                                domain=parsed.domain.value,
                                entity='lookup',
                                confidence=0.95,
                                term_type='lookup_groupby',
                                source='term_mapping_lookup'
                            )
                            term_matches = [synthetic_match] + term_matches
                    except Exception as lookup_err:
                        logger.warning(f"[DETERMINISTIC] Lookup mapping check failed: {lookup_err}")
                    
                    # Fall through to hardcoded synonyms if no lookup mapping found
                    if not group_by_column:
                        dimension_synonyms = {
                            'state': 'stateprovince',
                            'states': 'stateprovince',
                            'province': 'stateprovince',
                            'department': 'department',
                            'dept': 'department',
                            'location': 'location_code',
                            'status': 'employee_status',
                            'type': 'employee_type',
                            'company': 'company_code',
                            'job': 'job_code',
                            'job code': 'job_code',  # EVOLUTION 10: Multi-word
                            'pay': 'pay_group',
                            'pay group': 'pay_group',  # EVOLUTION 10: Multi-word
                            'pay period': 'pay_period',  # EVOLUTION 10: Multi-word
                            'gender': 'gender',
                            'city': 'city',
                            'country': 'country_code',
                            'employee type': 'employee_type',  # EVOLUTION 10: Multi-word
                            'employment status': 'employment_status_code',  # EVOLUTION 10: Multi-word
                            'term reason': 'termination_reason_code',  # EVOLUTION 10: Multi-word
                            'termination reason': 'termination_reason_code',  # EVOLUTION 10: Multi-word
                        }
                    
                        if group_by_dimension in dimension_synonyms:
                            column_name = dimension_synonyms[group_by_dimension]
                            logger.warning(f"[DETERMINISTIC] GROUP BY synonym: '{group_by_dimension}' → {column_name}")
                            
                            # EVOLUTION 10: Find a table with this column, prioritized by domain
                            # Use domain to determine table preference patterns
                            domain_table_patterns = {
                                'demographics': ['employee', 'personal', '_us_1_'],
                                'earnings': ['earning', 'pay', 'wage'],
                                'deductions': ['deduction', 'benefit'],
                                'taxes': ['tax', 'fit', 'sit', 'withhold'],
                                'time': ['time', 'attendance', 'schedule'],
                            }
                            
                            preferred_patterns = domain_table_patterns.get(parsed.domain.value, ['employee'])
                            
                            try:
                                # First try: Find table matching domain patterns (exclude config)
                                found_table = None
                                logger.warning(f"[DETERMINISTIC] Looking for column '{column_name}' in domain '{parsed.domain.value}' with patterns: {preferred_patterns}")
                                
                                # Debug: Show ALL tables that have this column
                                all_tables = term_index.conn.execute("""
                                    SELECT table_name, column_name FROM _column_profiles
                                    WHERE project = ? AND LOWER(column_name) = LOWER(?)
                                    LIMIT 10
                                """, [term_index.project, column_name]).fetchall()
                                if all_tables:
                                    logger.warning(f"[DETERMINISTIC] Tables with column '{column_name}': {[t[0][-30:] for t in all_tables]}")
                                else:
                                    logger.warning(f"[DETERMINISTIC] No tables found with column '{column_name}' in _column_profiles")
                                
                                for pattern in preferred_patterns:
                                    result = term_index.conn.execute("""
                                        SELECT DISTINCT table_name FROM _column_profiles
                                        WHERE project = ? 
                                        AND LOWER(column_name) = LOWER(?)
                                        AND LOWER(table_name) LIKE ?
                                        AND LOWER(table_name) NOT LIKE '%config%'
                                        AND LOWER(table_name) NOT LIKE '%validation%'
                                        ORDER BY table_name
                                        LIMIT 1
                                    """, [term_index.project, column_name, f'%{pattern}%']).fetchone()
                                    if result:
                                        found_table = result[0]
                                        logger.warning(f"[DETERMINISTIC] Found {parsed.domain.value} table with {column_name}: {found_table}")
                                        break
                                
                                # Fallback: Any non-config table with this column
                                if not found_table:
                                    result = term_index.conn.execute("""
                                        SELECT DISTINCT table_name FROM _column_profiles
                                        WHERE project = ? 
                                        AND LOWER(column_name) = LOWER(?)
                                        AND LOWER(table_name) NOT LIKE '%config%'
                                        AND LOWER(table_name) NOT LIKE '%validation%'
                                        ORDER BY table_name
                                        LIMIT 1
                                    """, [term_index.project, column_name]).fetchone()
                                    if result:
                                        found_table = result[0]
                                        logger.warning(f"[DETERMINISTIC] Found fallback table with {column_name}: {found_table}")
                                
                                if found_table:
                                    group_by_column = f"{found_table}.{column_name}"
                                    
                                    # Add synthetic match to term_matches
                                    from backend.utils.intelligence.term_index import TermMatch
                                    synthetic_match = TermMatch(
                                        term=column_name,
                                        table_name=found_table,
                                        column_name=column_name,
                                        operator='GROUP BY',
                                        match_value='',
                                        domain=parsed.domain.value,
                                        entity='employee' if parsed.domain.value == 'demographics' else 'unknown',
                                        confidence=0.85,
                                        term_type='synonym_lookup',
                                        source='synonym_table_lookup'
                                    )
                                    term_matches = [synthetic_match] + term_matches
                                    logger.warning(f"[DETERMINISTIC] Added synonym lookup table to term_matches: {found_table}")
                                else:
                                    group_by_column = column_name
                                    logger.warning(f"[DETERMINISTIC] No table found with column {column_name}, using column name only")
                            except Exception as e:
                                logger.warning(f"[DETERMINISTIC] Synonym table lookup failed: {e}")
                                group_by_column = column_name
                        else:
                            # Last resort: use the word as-is (might be a column name)
                            group_by_column = group_by_dimension
                            logger.warning(f"[DETERMINISTIC] GROUP BY using raw: '{group_by_dimension}'")
            
            # Step 5: Assemble SQL
            # EVOLUTION 8: Filter out concept matches - they're handled via group_by_column, not WHERE
            filter_matches = [m for m in term_matches if m.term_type != 'concept']
            if len(filter_matches) < len(term_matches):
                logger.warning(f"[DETERMINISTIC] Filtered out {len(term_matches) - len(filter_matches)} concept matches from WHERE clause")
            
            assembler = SQLAssembler(self.structured_handler.conn, self.project)
            assembled = assembler.assemble(
                intent=assembler_intent,
                term_matches=filter_matches,
                domain=parsed.domain.value,
                group_by_column=group_by_column
            )
            
            if not assembled.success:
                logger.warning(f"[DETERMINISTIC] Assembly failed: {assembled.error}")
                return build_cannot_resolve_response(
                    question=question,
                    reason=f"Could not assemble SQL query: {assembled.error}",
                    unresolved_terms=[m.term for m in filter_matches[:5]],
                    suggestions=[],
                    context={
                        'assembler_error': assembled.error,
                        'tables_involved': assembled.tables,
                        'intent': assembler_intent.value if hasattr(assembler_intent, 'value') else str(assembler_intent)
                    }
                )
            
            logger.warning(f"[DETERMINISTIC] Assembled SQL: {assembled.sql}")
            
            # Step 5: Execute SQL
            try:
                result = self.structured_handler.conn.execute(assembled.sql).fetchall()
                columns = [desc[0] for desc in self.structured_handler.conn.description]
                
                logger.warning(f"[DETERMINISTIC] Executed: {len(result)} rows returned")
            except Exception as sql_error:
                logger.error(f"[DETERMINISTIC] SQL execution error: {sql_error}")
                return build_system_error_response(
                    question=question,
                    error=f"SQL execution failed: {str(sql_error)[:200]}",
                    component="sql_execution",
                    context={
                        'sql': assembled.sql[:500],
                        'tables': assembled.tables,
                        'error_type': type(sql_error).__name__
                    }
                )
            
            if not result:
                logger.warning(f"[DETERMINISTIC] No results found - returning no_data response")
                return build_no_data_response(
                    question=question,
                    sql=assembled.sql,
                    filters_applied=assembled.filters,
                    table_name=assembled.primary_table,
                    context={
                        'intent': assembler_intent.value if hasattr(assembler_intent, 'value') else str(assembler_intent),
                        'tables': assembled.tables
                    }
                )
            
            # Step 6: Build response
            rows = [dict(zip(columns, row)) for row in result]
            
            # EVOLUTION 8: Check if this is a GROUP BY query (multiple rows with dimension)
            is_group_by = group_by_column and len(rows) > 1
            
            # Convert assembled.filters to format expected by templates
            filter_list = []
            if assembled.filters:
                for f in assembled.filters:
                    if isinstance(f, dict):
                        filter_list.append(f)
                    elif hasattr(f, 'column_name'):
                        # TermMatch object
                        filter_list.append({
                            'column': f.column_name,
                            'operator': f.operator,
                            'value': f.match_value
                        })
            
            # Build consultative answer text using templates
            if is_group_by:
                # GROUP BY query - breakdown response
                dim_col = columns[0]  # First column is the dimension
                agg_col = columns[1] if len(columns) > 1 else 'count'
                
                answer_text = format_group_by_response(
                    rows=rows,
                    dimension_column=dim_col,
                    value_column=agg_col,
                    agg_type=parsed.intent.value,
                    table_name=assembled.primary_table,
                    filters=filter_list
                )
                logger.warning(f"[DETERMINISTIC] GROUP BY result: {len(rows)} groups (consultative template)")
                
            elif assembler_intent == AssemblerIntent.COUNT:
                count = rows[0].get('count', len(rows)) if rows else 0
                answer_text = format_count_response(
                    count=count,
                    entity=parsed.domain.value if parsed.domain else 'records',
                    table_name=assembled.primary_table,
                    filters=filter_list,
                    project=self.project,
                    sql=assembled.sql
                )
                
            elif assembler_intent == AssemblerIntent.SUM:
                total = rows[0].get('total', 0) if rows else 0
                answer_text = format_aggregation_response(
                    agg_type='sum',
                    value=total,
                    column=assembled.agg_column if hasattr(assembled, 'agg_column') else 'total',
                    table_name=assembled.primary_table,
                    filters=filter_list,
                    row_count=len(result)
                )
                
            elif assembler_intent == AssemblerIntent.AVERAGE:
                avg = rows[0].get('average', 0) if rows else 0
                answer_text = format_aggregation_response(
                    agg_type='average',
                    value=avg,
                    column=assembled.agg_column if hasattr(assembled, 'agg_column') else 'value',
                    table_name=assembled.primary_table,
                    filters=filter_list,
                    row_count=len(result)
                )
                
            elif assembler_intent == AssemblerIntent.MINIMUM:
                minimum = rows[0].get('minimum', 0) if rows else 0
                answer_text = format_aggregation_response(
                    agg_type='minimum',
                    value=minimum,
                    column=assembled.agg_column if hasattr(assembled, 'agg_column') else 'value',
                    table_name=assembled.primary_table,
                    filters=filter_list
                )
                
            elif assembler_intent == AssemblerIntent.MAXIMUM:
                maximum = rows[0].get('maximum', 0) if rows else 0
                answer_text = format_aggregation_response(
                    agg_type='maximum',
                    value=maximum,
                    column=assembled.agg_column if hasattr(assembled, 'agg_column') else 'value',
                    table_name=assembled.primary_table,
                    filters=filter_list
                )
                
            else:
                # LIST intent or fallback
                answer_text = format_list_response(
                    rows=rows[:100],
                    columns=columns,
                    table_name=assembled.primary_table,
                    total_count=len(rows),
                    filters=filter_list,
                    entity=parsed.domain.value if parsed.domain else 'records'
                )
            
            # Build structured output using proper Truth objects
            reality_truth = Truth(
                source_type='reality',
                source_name=assembled.primary_table,
                content={
                    'columns': columns,
                    'rows': rows[:100],  # Limit to 100 for display
                    'total': len(rows),
                    'query_type': parsed.intent.value,
                    'sql': assembled.sql
                },
                confidence=0.95,
                location=f"DuckDB: {assembled.primary_table}",
                metadata={
                    'filters': assembled.filters,
                    'deterministic': True
                }
            )
            
            return SynthesizedAnswer(
                question=question,
                answer=answer_text,
                confidence=0.9,
                from_reality=[reality_truth],
                reasoning=[
                    f"Used deterministic path (Term Index + SQL Assembler)",
                    f"Intent: {parsed.intent.value}",
                    f"Tables: {', '.join(assembled.tables)}",
                    f"Filters: {len(assembled.filters)} applied via term index",
                    f"SQL: {assembled.sql[:100]}..."
                ],
                structured_output={
                    'type': 'data_result',
                    'intent': parsed.intent.value,
                    'tables': assembled.tables,
                    'filters': assembled.filters,
                    'row_count': len(rows),
                    'sql': assembled.sql
                }
            )
            
        except Exception as e:
            logger.error(f"[DETERMINISTIC] Error: {e}")
            import traceback
            tb = traceback.format_exc()
            logger.error(f"[DETERMINISTIC] Traceback: {tb}")
            return build_system_error_response(
                question=question,
                error=str(e)[:200],
                component="deterministic_path",
                context={'traceback': tb[:500]}
            )
    
    def _try_multi_hop_query(self, question: str, multi_hop_info: Dict) -> Optional[SynthesizedAnswer]:
        """
        Evolution 10: Handle multi-hop relationship queries.
        
        Processes queries like:
        - "manager's department" - self-join through supervisor_id
        - "employees in John's team" - filter by supervisor name
        - "location's regional manager" - multi-hop join
        
        Args:
            question: The original question
            multi_hop_info: Parsed relationship info from detect_multi_hop_query()
            
        Returns:
            SynthesizedAnswer if successful, None to fall back to regular path
        """
        logger.warning(f"[MULTI-HOP] Processing multi-hop query: {multi_hop_info}")
        
        if not DETERMINISTIC_PATH_AVAILABLE:
            return None
        
        if not self.structured_handler:
            return None
        
        try:
            # Get primary table from the stored relationship (not from hub guessing)
            semantic = multi_hop_info.get('semantic', 'supervisor')
            
            relationship = self.structured_handler.conn.execute("""
                SELECT source_table, source_column, target_column
                FROM _column_relationships
                WHERE LOWER(project) = LOWER(?)
                AND semantic_meaning = ?
                LIMIT 1
            """, [self.project, semantic]).fetchone()
            
            if not relationship:
                logger.warning(f"[MULTI-HOP] No relationship found for semantic='{semantic}'")
                return None
            
            primary_table = relationship[0]
            logger.warning(f"[MULTI-HOP] Found relationship in table: {primary_table}")
            
            # Build the multi-hop request
            traversal_type = multi_hop_info.get('traversal_type')
            
            if traversal_type == 'possessive':
                # "manager's department" pattern
                multi_hop = MultiHopRequest(
                    relationship_type=multi_hop_info.get('semantic', 'supervisor'),
                    target_attribute=multi_hop_info.get('target_attribute', ''),
                    direction=multi_hop_info.get('direction', 'forward')
                )
            elif traversal_type == 'named_possessive':
                # "John's team" pattern - filter by name
                multi_hop = MultiHopRequest(
                    relationship_type='supervisor',
                    target_attribute=multi_hop_info.get('target_attribute', 'name'),
                    direction='reverse',
                    filter_value=multi_hop_info.get('source_entity')
                )
            elif traversal_type == 'keyword':
                # "reports to X" pattern
                multi_hop = MultiHopRequest(
                    relationship_type=multi_hop_info.get('semantic', 'supervisor'),
                    target_attribute='name',
                    direction=multi_hop_info.get('direction', 'forward')
                )
            else:
                logger.warning(f"[MULTI-HOP] Unknown traversal type: {traversal_type}")
                return None
            
            logger.warning(f"[MULTI-HOP] Built request: {multi_hop}")
            
            # Build the multi-hop SQL
            assembler = SQLAssembler(self.structured_handler.conn, self.project)
            result = assembler.build_multi_hop_query(
                primary_table=primary_table,
                multi_hop=multi_hop,
                limit=100
            )
            
            if not result.success:
                logger.warning(f"[MULTI-HOP] Query build failed: {result.error}")
                return None
            
            logger.warning(f"[MULTI-HOP] Generated SQL: {result.sql[:200]}...")
            
            # Execute the query
            try:
                rows = self.structured_handler.conn.execute(result.sql).fetchdf().to_dict('records')
            except Exception as exec_err:
                logger.error(f"[MULTI-HOP] SQL execution failed: {exec_err}")
                return None
            
            if not rows:
                logger.warning("[MULTI-HOP] No results returned")
                return None
            
            # Build the answer
            target_attr = multi_hop.target_attribute
            result_col = result.multi_hop_info.get('result_column', f'mgr_{target_attr}') if result.multi_hop_info else f'mgr_{target_attr}'
            
            # Get unique values for the target attribute from results
            target_values = []
            for row in rows[:20]:  # Sample first 20
                val = row.get(result_col)
                if val and val not in target_values:
                    target_values.append(val)
            
            # Build response text based on query type
            if traversal_type == 'possessive':
                if len(target_values) == 1:
                    answer_text = f"✅ The {multi_hop_info.get('source_entity', 'manager')}'s {target_attr} is: {target_values[0]}"
                else:
                    values_list = ', '.join(str(v) for v in target_values[:10])
                    answer_text = f"✅ Found {len(rows)} employees. Their {multi_hop_info.get('source_entity', 'manager')}s' {target_attr}s include: {values_list}"
            elif traversal_type == 'named_possessive':
                name = multi_hop_info.get('source_entity', 'unknown')
                answer_text = f"✅ Found {len(rows)} employees in {name}'s team."
            else:
                answer_text = f"✅ Found {len(rows)} records with relationship data."
            
            # Get columns
            columns = list(rows[0].keys()) if rows else []
            
            # Build Truth object
            reality_truth = Truth(
                source_type='reality',
                source_name=primary_table,
                content={
                    'columns': columns,
                    'rows': rows[:100],
                    'total': len(rows),
                    'query_type': 'multi_hop',
                    'sql': result.sql
                },
                confidence=0.9,
                location=f"DuckDB: {primary_table} (self-join)",
                metadata={
                    'multi_hop': True,
                    'relationship': multi_hop.relationship_type,
                    'target_attribute': multi_hop.target_attribute
                }
            )
            
            return SynthesizedAnswer(
                question=question,
                answer=answer_text,
                confidence=0.85,
                from_reality=[reality_truth],
                reasoning=[
                    f"Used multi-hop relationship query (Evolution 10)",
                    f"Relationship: {multi_hop.relationship_type}",
                    f"Target attribute: {multi_hop.target_attribute}",
                    f"Result: {len(rows)} records"
                ],
                structured_output={
                    'type': 'multi_hop_result',
                    'relationship': multi_hop.relationship_type,
                    'target': multi_hop.target_attribute,
                    'row_count': len(rows),
                    'sql': result.sql
                }
            )
            
        except Exception as e:
            logger.error(f"[MULTI-HOP] Error: {e}")
            import traceback
            logger.error(f"[MULTI-HOP] Traceback: {traceback.format_exc()}")
            return None
    
    # =========================================================================
    # CLARIFICATION HANDLING - v9.0 Intelligent Filter Detection
    # =========================================================================
    
    def _build_filter_vocabulary(self) -> Dict[str, Dict[str, str]]:
        """
        Build a vocabulary mapping natural language terms to filter values.
        
        Returns: Dict[category, Dict[term, value]]
        Example: {'status': {'active': 'A', 'terminated': 'T'}}
        
        Uses:
        1. Standard patterns for common categories (domain-agnostic)
        2. Lookups from project intelligence (data-driven)
        3. Direct value matching (fallback)
        """
        vocab = {}
        
        for category, candidates in self.filter_candidates.items():
            if not candidates:
                continue
            
            # Get distinct values from the primary candidate
            primary = candidates[0] if candidates else {}
            values = primary.get('distinct_values', [])
            
            if not values:
                continue
            
            term_map = {}
            values_upper = [str(v).upper().strip() for v in values if v]
            
            # Category-specific mappings (common HCM patterns, not vendor-specific)
            if category == 'status':
                # Employment status is universal: Active, Terminated, Leave
                for v in values:
                    v_upper = str(v).upper().strip() if v else ''
                    if v_upper in ('A', 'ACTIVE'):
                        term_map['active'] = v
                        term_map['current'] = v
                        term_map['employed'] = v
                    elif v_upper in ('T', 'TERMINATED', 'TERM'):
                        term_map['terminated'] = v
                        term_map['termed'] = v
                        term_map['former'] = v
                        term_map['ex-employee'] = v
                    elif v_upper in ('L', 'LOA', 'LEAVE'):
                        term_map['leave'] = v
                        term_map['loa'] = v
                        term_map['on leave'] = v
                        
            elif category == 'location':
                # US state names → codes (common in HCM)
                state_map = {
                    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
                    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
                    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
                    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
                    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
                    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
                    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
                    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
                    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
                    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
                    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
                    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
                    'wisconsin': 'WI', 'wyoming': 'WY',
                    # Canadian provinces
                    'ontario': 'ON', 'quebec': 'QC', 'british columbia': 'BC', 'alberta': 'AB',
                }
                for name, code in state_map.items():
                    if code in values_upper:
                        term_map[name] = code
            
            # Also use lookups if available (data-driven, not hardcoded)
            if hasattr(self, 'project_intelligence') and self.project_intelligence:
                pi = self.project_intelligence
                if hasattr(pi, 'lookups') and pi.lookups:
                    for lookup in pi.lookups:
                        if hasattr(lookup, 'lookup_type') and hasattr(lookup, 'lookup_data'):
                            # Match lookup type to filter category
                            if lookup.lookup_type.lower() in category.lower() or category.lower() in lookup.lookup_type.lower():
                                # Reverse the mapping: description → code
                                for code, desc in lookup.lookup_data.items():
                                    if desc and code:
                                        term_map[desc.lower()] = code
            
            # Direct value matching (case-insensitive)
            # But skip 2-letter values that are common English words
            SKIP_VALUES = {'in', 'on', 'ok', 'hi', 'me', 'or', 'no', 'so', 'to', 'we', 'us', 'be', 'am', 'is', 'it', 'an', 'as', 'at', 'by', 'do', 'go', 'he', 'if', 'my', 'of', 'up'}
            for v in values:
                if v:
                    v_str = str(v).strip()
                    v_lower = v_str.lower()
                    # Skip if it's a common English word
                    if v_lower in SKIP_VALUES:
                        continue
                    term_map[v_lower] = v_str
            
            if term_map:
                vocab[category] = term_map
                
        return vocab
    
    def _detect_filters_from_question(self, question: str) -> Dict[str, str]:
        """
        Detect filter values mentioned in the question.
        
        Returns: Dict[category, detected_value]
        Example: {'status': 'A'} if question contains "active employees"
        
        This is DOMAIN-AGNOSTIC - it uses the filter vocabulary built from
        the actual data, not hardcoded business rules.
        
        v5.0: Now tries term index first (load-time intelligence) before
        falling back to vocabulary matching.
        """
        detected = {}
        q_lower = question.lower()
        
        # =================================================================
        # PRIORITY 1: Try term index (load-time intelligence)
        # Term index knows entity types (location vs company vs status)
        # EVOLUTION 3: Also handles numeric expressions
        # =================================================================
        try:
            from backend.utils.intelligence.term_index import TermIndex
            if hasattr(self, 'structured_handler') and self.structured_handler:
                term_index = TermIndex(self.structured_handler.conn, self.project)
                
                # Extract words from question
                words = re.findall(r'\b[a-zA-Z]{2,}\b', q_lower)
                
                # EVOLUTION 3: Also extract numeric phrases
                numeric_phrase_patterns = [
                    r'(?:above|over|more than|greater than)\s+[\$]?\d[\d,]*[kKmM]?',
                    r'(?:below|under|less than)\s+[\$]?\d[\d,]*[kKmM]?',
                    r'(?:at least|minimum)\s+[\$]?\d[\d,]*[kKmM]?',
                    r'(?:at most|maximum)\s+[\$]?\d[\d,]*[kKmM]?',
                    r'between\s+[\$]?\d[\d,]*[kKmM]?\s+and\s+[\$]?\d[\d,]*[kKmM]?',
                ]
                numeric_phrases = []
                for pattern in numeric_phrase_patterns:
                    found = re.findall(pattern, q_lower)
                    numeric_phrases.extend(found)
                
                # EVOLUTION 4: Date phrase patterns
                date_phrase_patterns = [
                    r'(?:last|this|next)\s+(?:year|month|quarter|week)',
                    r'(?:in|during)\s+(?:20\d{2})',
                    r'(?:in|during)\s+q[1-4]',
                ]
                date_phrases = []
                for pattern in date_phrase_patterns:
                    found = re.findall(pattern, q_lower)
                    date_phrases.extend(found)
                
                # EVOLUTION 5: OR phrase patterns
                or_pattern = r'(\w+)\s+or\s+(\w+)'
                or_matches = re.findall(or_pattern, q_lower)
                or_phrases = [f"{m[0]} or {m[1]}" for m in or_matches]
                
                # EVOLUTION 6: Negation phrase patterns (with position tracking to avoid duplicates)
                negation_phrases = []
                matched_positions = set()
                
                # First: "not in X" pattern (most specific)
                for match in re.finditer(r'not\s+in\s+(\w+)', q_lower):
                    negation_phrases.append(f"not {match.group(1)}")
                    matched_positions.add(match.start())
                
                # Second: "not X" but skip if already matched by "not in X"
                for match in re.finditer(r'not\s+(\w+)', q_lower):
                    if match.start() not in matched_positions:
                        term = match.group(1)
                        if term != 'in':  # Skip standalone "not in"
                            negation_phrases.append(f"not {term}")
                
                # Other negation keywords
                for pattern in [r'excluding\s+(\w+)', r'except\s+(\w+)', r'without\s+(\w+)']:
                    for match in re.finditer(pattern, q_lower):
                        negation_phrases.append(f"not {match.group(1)}")
                
                # Filter out words that are part of phrases
                phrase_words = set()
                if numeric_phrases:
                    for phrase in numeric_phrases:
                        phrase_words.update(phrase.split())
                if date_phrases:
                    for phrase in date_phrases:
                        phrase_words.update(phrase.split())
                if or_phrases:
                    for phrase in or_phrases:
                        phrase_words.update(phrase.split())
                if negation_phrases:
                    for phrase in negation_phrases:
                        phrase_words.update(phrase.split())
                    phrase_words.update(['not', 'in', 'excluding', 'except', 'without'])
                if phrase_words:
                    words = [w for w in words if w not in phrase_words]
                
                terms_to_resolve = words + numeric_phrases + date_phrases + or_phrases + negation_phrases
                
                # Resolve via term index (use enhanced if available)
                if hasattr(term_index, 'resolve_terms_enhanced'):
                    matches = term_index.resolve_terms_enhanced(terms_to_resolve, detect_numeric=True, detect_dates=True, detect_or=True, detect_negation=True)
                else:
                    matches = term_index.resolve_terms(terms_to_resolve)
                for match in matches:
                    # Map entity to filter category
                    entity = match.entity or ''
                    if entity == 'location':
                        if 'location' not in detected:
                            detected['location'] = match.match_value
                            logger.warning(f"[FILTER] Term index: '{match.term}' → location='{match.match_value}'")
                    elif entity == 'status':
                        if 'status' not in detected:
                            detected['status'] = match.match_value
                            logger.warning(f"[FILTER] Term index: '{match.term}' → status='{match.match_value}'")
        except Exception as e:
            logger.debug(f"Term index filter detection error: {e}")
        
        # =================================================================
        # PRIORITY 2: Vocabulary-based matching (fallback)
        # =================================================================
        # Build vocabulary on first use (cached on engine instance)
        if not hasattr(self, '_filter_vocab_cache'):
            self._filter_vocab_cache = self._build_filter_vocabulary()
        
        vocab = self._filter_vocab_cache
        
        for category, term_map in vocab.items():
            # Skip if term index already found this category
            if category in detected:
                continue
                
            # Sort terms by length (descending) to match longer phrases first
            sorted_terms = sorted(term_map.keys(), key=len, reverse=True)
            
            for term in sorted_terms:
                # Check for word boundary matches to avoid partial matches
                # e.g., "active" should match but "proactive" should not
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, q_lower):
                    detected[category] = term_map[term]
                    logger.warning(f"[CLARIFICATION] Auto-detected {category}='{term_map[term]}' from term '{term}'")
                    break  # First match per category
        
        return detected
    
    def _check_clarification_needed(self, question: str, 
                                    q_lower: str) -> Optional[SynthesizedAnswer]:
        """
        Check if clarification is needed for employee questions.
        
        v9.0: Now uses intelligent filter detection:
        1. Check if filters are already in confirmed_facts
        2. Detect filters from question text
        3. Only ask if truly ambiguous
        """
        # Step 1: Detect filters from question text
        detected = self._detect_filters_from_question(question)
        
        # Step 2: Auto-populate confirmed_facts with detected filters
        for category, value in detected.items():
            if category not in self.confirmed_facts:
                self.confirmed_facts[category] = value
                logger.warning(f"[CLARIFICATION] Auto-applied {category}='{value}' to confirmed_facts")
        
        # v9.1: Sync confirmed_facts to sql_generator so it knows about detected filters
        if detected and self.sql_generator:
            self.sql_generator.confirmed_facts = self.confirmed_facts
            logger.warning(f"[CLARIFICATION] Synced confirmed_facts to sql_generator")
        
        # Step 3: Check if status clarification is still needed
        if 'status' not in self.confirmed_facts:
            if 'status' in self.filter_candidates:
                # Only ask if we have status filter candidates
                return self._build_status_clarification(question)
        
        return None
    
    def _build_status_clarification(self, question: str) -> SynthesizedAnswer:
        """Build status clarification request with actual counts from data."""
        # Get actual counts if available
        status_candidates = self.filter_candidates.get('status', [])
        
        options = []
        if status_candidates:
            primary = status_candidates[0]
            distribution = primary.get('value_distribution', {})
            
            # Build options from actual data
            active_count = distribution.get('A', 0)
            termed_count = distribution.get('T', 0)
            loa_count = distribution.get('L', 0)
            total_count = active_count + termed_count + loa_count
            
            if active_count:
                options.append({'id': 'active', 'label': f'Active employees only ({active_count:,})'})
            if termed_count:
                options.append({'id': 'termed', 'label': f'Terminated employees only ({termed_count:,})'})
            if total_count:
                options.append({'id': 'all', 'label': f'All employees ({total_count:,})'})
        
        if not options:
            # Fallback if no distribution data
            options = [
                {'id': 'active', 'label': 'Active employees only'},
                {'id': 'termed', 'label': 'Terminated employees only'},
                {'id': 'all', 'label': 'All employees (active + terminated)'}
            ]
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': [{
                    'id': 'status',
                    'question': 'Which employees would you like to include?',
                    'type': 'radio',
                    'options': options
                }],
                'original_question': question
            },
            reasoning=['Need to clarify employee status filter']
        )
    
    def _handle_comparison(self, question: str, q_lower: str) -> Optional[SynthesizedAnswer]:
        """
        Handle comparison queries using the ComparisonEngine.
        
        Uses TableSelector to find the best matching tables for each reference,
        leveraging all the classification/domain intelligence we built.
        """
        logger.warning(f"[ENGINE-V2] Handling comparison query: {question[:60]}...")
        
        if not self.schema or not self.schema.get('tables'):
            logger.warning("[ENGINE-V2] No schema available for comparison")
            return None
        
        # Parse question to extract the two table references
        ref_a, ref_b = self._extract_comparison_references(q_lower)
        
        if not ref_a or not ref_b:
            logger.warning(f"[ENGINE-V2] Could not extract two table references from query")
            return None
        
        logger.warning(f"[ENGINE-V2] Extracted references: A='{ref_a}', B='{ref_b}'")
        
        # Use TableSelector to find best match for EACH reference
        # This uses all our classification intelligence (domain, truth_type, etc.)
        tables = self.schema.get('tables', [])
        
        # Find best table for reference A
        table_a = self._find_table_for_reference(ref_a, tables, exclude=None)
        if not table_a:
            logger.warning(f"[ENGINE-V2] No table found for reference A: {ref_a}")
            return None
        
        # Find best table for reference B (excluding table A)
        table_b = self._find_table_for_reference(ref_b, tables, exclude=table_a)
        if not table_b:
            logger.warning(f"[ENGINE-V2] No table found for reference B: {ref_b}")
            return None
        
        if table_a == table_b:
            logger.warning(f"[ENGINE-V2] Both references matched same table: {table_a}")
            return None
        
        logger.warning(f"[ENGINE-V2] Comparing: {table_a} vs {table_b}")
        
        try:
            # Run comparison
            engine = ComparisonEngine(structured_handler=self.structured_handler)
            result = engine.compare(
                table_a=table_a,
                table_b=table_b,
                customer_id=self.customer_id
            )
            
            # Format consultative response
            answer = self._format_comparison_result(result, question)
            
            return SynthesizedAnswer(
                question=question,
                answer=answer,
                confidence=0.92,
                structured_output={
                    'type': 'comparison',
                    'result': result.to_dict()
                },
                reasoning=[
                    f"Compared {result.source_a_rows} rows from {table_a}",
                    f"Compared {result.source_b_rows} rows from {table_b}",
                    f"Found {result.matches} matches, {len(result.only_in_a)} only in A, {len(result.only_in_b)} only in B"
                ]
            )
            
        except Exception as e:
            logger.error(f"[ENGINE-V2] Comparison failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_comparison_references(self, q_lower: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract the two table references from a comparison question.
        
        Returns the raw reference strings, NOT table names.
        e.g., "Company Tax Verification" and "Company Master Profile"
        """
        # Patterns to extract the two things being compared
        patterns = [
            # "compare X to Y and tell me..."
            r'compare\s+(?:the\s+)?(?:tax\s+codes\s+in\s+)?(.+?)\s+to\s+(.+?)(?:\s+and\s+tell|\s+and\s+show|\s*$)',
            # "compare X with Y"
            r'compare\s+(.+?)\s+(?:with|vs|versus)\s+(.+?)(?:\s+and|\s*$)',
            # "X compared to Y"
            r'(.+?)\s+compared\s+to\s+(.+?)(?:\s+and|\s*$)',
            # "difference between X and Y"
            r'difference\s+between\s+(.+?)\s+and\s+(.+?)(?:\s*$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, q_lower)
            if match:
                ref_a = match.group(1).strip()
                ref_b = match.group(2).strip()
                
                # Clean up common prefixes
                for prefix in ['the ', 'my ', 'our ']:
                    if ref_a.startswith(prefix):
                        ref_a = ref_a[len(prefix):]
                    if ref_b.startswith(prefix):
                        ref_b = ref_b[len(prefix):]
                
                if ref_a and ref_b:
                    return ref_a, ref_b
        
        return None, None
    
    def _find_table_for_reference(self, reference: str, tables: List[Dict], 
                                   exclude: str = None) -> Optional[str]:
        """
        Find the best matching table for a reference string.
        
        Uses TableSelector with the reference as the "question" to leverage
        all our classification intelligence.
        """
        # Filter out excluded table
        if exclude:
            tables = [t for t in tables if t.get('table_name') != exclude]
        
        if not tables:
            return None
        
        # Use TableSelector to score tables against this reference
        selector = TableSelector(
            structured_handler=self.structured_handler,
            filter_candidates=self.filter_candidates,
            project=self.customer_id
        )
        
        # Select best matches for this reference
        matches = selector.select(tables, reference, max_tables=3)
        
        if matches:
            best_match = matches[0].get('table_name')
            logger.warning(f"[ENGINE-V2] Reference '{reference[:30]}' -> {best_match}")
            return best_match
        
        return None
    
    def _format_comparison_result(self, result, question: str) -> str:
        """Format comparison result as consultative answer."""
        parts = []
        
        # Summary
        parts.append(f"## Comparison: {result.source_a} vs {result.source_b}\n")
        
        # Key metrics
        parts.append(f"**Match Rate:** {result.match_rate:.1%}")
        parts.append(f"- **Matched:** {result.matches} records")
        parts.append(f"- **Only in {result.source_a}:** {len(result.only_in_a)} records")
        parts.append(f"- **Only in {result.source_b}:** {len(result.only_in_b)} records")
        
        if result.mismatches:
            parts.append(f"- **Value Mismatches:** {len(result.mismatches)} records")
        
        # Show what's missing
        if result.only_in_a:
            parts.append(f"\n### Missing from {result.source_b}:")
            # Get key column values
            key_col = result.join_keys[0] if result.join_keys else None
            if key_col:
                missing_values = [str(r.get(key_col, ''))[:30] for r in result.only_in_a[:10]]
                for val in missing_values:
                    parts.append(f"- `{val}`")
                if len(result.only_in_a) > 10:
                    parts.append(f"- *...and {len(result.only_in_a) - 10} more*")
        
        if result.only_in_b:
            parts.append(f"\n### Missing from {result.source_a}:")
            key_col = result.join_keys[0] if result.join_keys else None
            if key_col:
                missing_values = [str(r.get(key_col, ''))[:30] for r in result.only_in_b[:10]]
                for val in missing_values:
                    parts.append(f"- `{val}`")
                if len(result.only_in_b) > 10:
                    parts.append(f"- *...and {len(result.only_in_b) - 10} more*")
        
        # Mismatches
        if result.mismatches:
            parts.append(f"\n### Value Differences:")
            for mismatch in result.mismatches[:5]:
                keys = mismatch.get('keys', {})
                key_str = ", ".join([f"{k}={v}" for k, v in keys.items()])
                parts.append(f"- **{key_str}**:")
                for diff in mismatch.get('differences', [])[:3]:
                    parts.append(f"  - {diff['column']}: `{diff['value_a']}` → `{diff['value_b']}`")
        
        # Recommendation
        parts.append("\n### Recommendation:")
        if result.match_rate >= 0.95:
            parts.append("✅ **High alignment** - Only minor discrepancies to review.")
        elif result.match_rate >= 0.7:
            parts.append("⚠️ **Moderate alignment** - Review the gaps above to ensure data consistency.")
        else:
            parts.append("🔴 **Low alignment** - Significant discrepancies require immediate attention.")
        
        return "\n".join(parts)
    
    def _handle_export_request(self, question: str, 
                               q_lower: str) -> Optional[SynthesizedAnswer]:
        """Handle export/download requests."""
        export_keywords = ['export', 'download', 'excel', 'csv', 'spreadsheet']
        is_export = any(kw in q_lower for kw in export_keywords)
        
        if is_export and self._last_validation_export:
            export_data = self._last_validation_export
            return SynthesizedAnswer(
                question=question,
                answer=f"📥 **Export Ready**\n\n{export_data['total_records']} records prepared.",
                confidence=0.95,
                structured_output={
                    'type': 'export_ready',
                    'export_data': export_data
                },
                reasoning=['Export requested']
            )
        
        return None
    
    # =========================================================================
    # TRUTH GATHERING
    # =========================================================================
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Reality truths from DuckDB."""
        if not self.reality_gatherer:
            return []
        
        truths = self.reality_gatherer.gather(question, analysis)
        
        # Check for pending clarification
        if analysis.get('pending_clarification'):
            self._pending_clarification = analysis['pending_clarification']
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Intent truths from customer documents."""
        if self.intent_gatherer:
            return self.intent_gatherer.gather(question, analysis)
        return []
    
    def _gather_configuration(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather Configuration truths from config tables.
        
        NOTE: Configuration uses DuckDB (code tables, mappings), NOT ChromaDB.
        This was a bug in the previous implementation that searched ChromaDB.
        """
        if self.configuration_gatherer:
            return self.configuration_gatherer.gather(question, analysis)
        return []
    
    def _gather_reference_library(self, question: str, 
                                  analysis: Dict) -> Tuple[List[Truth], List[Truth], List[Truth]]:
        """
        Gather Reference Library truths (global scope).
        
        Returns:
            Tuple of (reference, regulatory, compliance) Truth lists
            
        These are GLOBAL - they apply to all projects and are not filtered by customer_id.
        
        Phase 2B.2: Now uses TruthRouter to determine which truth types to gather
        based on query patterns. This improves relevance and reduces noise.
        """
        reference = []
        regulatory = []
        compliance = []
        
        # Phase 2B.2: Use TruthRouter to determine which truths to gather
        if TRUTH_ROUTER_AVAILABLE and truth_router_instance:
            routing = truth_router_instance.route_query(question, analysis)
            
            # Log routing decision
            truth_types = [tq.truth_type for tq in routing.queries]
            logger.warning(f"[GATHER-LIBRARY] TruthRouter: {routing.query_category} → {truth_types}")
            
            # Only gather truths that the router recommends
            # Use weight threshold of 0.3 to include moderately relevant truths
            should_ref, ref_weight = truth_router_instance.should_gather('reference', routing, 0.3)
            should_reg, reg_weight = truth_router_instance.should_gather('regulatory', routing, 0.3)
            should_comp, comp_weight = truth_router_instance.should_gather('compliance', routing, 0.3)
            
            if should_ref and self.reference_gatherer:
                reference = self.reference_gatherer.gather(question, analysis)
                # Tag results with routing weight for later prioritization
                for t in reference:
                    t.metadata = t.metadata or {}
                    t.metadata['routing_weight'] = ref_weight
                    
            if should_reg and self.regulatory_gatherer:
                regulatory = self.regulatory_gatherer.gather(question, analysis)
                for t in regulatory:
                    t.metadata = t.metadata or {}
                    t.metadata['routing_weight'] = reg_weight
                    
            if should_comp and self.compliance_gatherer:
                compliance = self.compliance_gatherer.gather(question, analysis)
                for t in compliance:
                    t.metadata = t.metadata or {}
                    t.metadata['routing_weight'] = comp_weight
            
            # Store routing info in analysis for downstream use
            analysis['truth_routing'] = {
                'category': routing.query_category,
                'domain': routing.domain_detected,
                'confidence': routing.confidence,
                'reasoning': routing.reasoning
            }
            
            # Phase 2B.4: Multi-factor relevance scoring and filtering
            # (Supersedes 2B.3 SourcePrioritizer - includes authority + recency + jurisdiction)
            if RELEVANCE_SCORER_AVAILABLE and relevance_scorer_instance:
                query_category = routing.query_category
                query_domain = routing.domain_detected
                # Extract jurisdiction from analysis if available
                query_jurisdiction = analysis.get('jurisdiction') or analysis.get('state')
                
                if reference:
                    reference = relevance_scorer_instance.score_and_filter_truths(
                        reference, query_category, query_domain, query_jurisdiction
                    )
                if regulatory:
                    regulatory = relevance_scorer_instance.score_and_filter_truths(
                        regulatory, query_category, query_domain, query_jurisdiction
                    )
                if compliance:
                    compliance = relevance_scorer_instance.score_and_filter_truths(
                        compliance, query_category, query_domain, query_jurisdiction
                    )
                    
                logger.warning(f"[GATHER-LIBRARY] Applied multi-factor relevance scoring")
            
            # Fallback to 2B.3 SourcePrioritizer if RelevanceScorer not available
            elif SOURCE_PRIORITIZER_AVAILABLE and source_prioritizer_instance:
                query_category = routing.query_category
                query_domain = routing.domain_detected
                
                if reference:
                    reference = source_prioritizer_instance.prioritize_truths(
                        reference, query_category, query_domain
                    )
                if regulatory:
                    regulatory = source_prioritizer_instance.prioritize_truths(
                        regulatory, query_category, query_domain
                    )
                if compliance:
                    compliance = source_prioritizer_instance.prioritize_truths(
                        compliance, query_category, query_domain
                    )
                    
                logger.warning(f"[GATHER-LIBRARY] Re-ranked results by source authority")
        else:
            # Fallback: gather from all truth types (original behavior)
            if self.reference_gatherer:
                reference = self.reference_gatherer.gather(question, analysis)
                
            if self.regulatory_gatherer:
                regulatory = self.regulatory_gatherer.gather(question, analysis)
                
            if self.compliance_gatherer:
                compliance = self.compliance_gatherer.gather(question, analysis)
        
        # Phase 2B.5: Collect citations from all gathered truths
        if CITATION_TRACKER_AVAILABLE and CitationCollector:
            try:
                collector = CitationCollector()
                collector.set_question(question)
                
                # Add citations from each truth type
                for truth in reference:
                    collector.add_from_truth(truth)
                for truth in regulatory:
                    collector.add_from_truth(truth)
                for truth in compliance:
                    collector.add_from_truth(truth)
                
                # Store in analysis for downstream use
                analysis['citations'] = [c.to_dict() for c in collector.get_top_citations(10)]
                analysis['citation_summary'] = collector.summary()
                analysis['citation_bibliography'] = collector.format_bibliography()
                
                logger.warning(f"[GATHER-LIBRARY] Collected citations: {collector.summary()}")
            except Exception as e:
                logger.warning(f"[GATHER-LIBRARY] Citation collection failed: {e}")
        
        # Phase 2B.6: Detect gaps in truth coverage
        if GAP_DETECTOR_AVAILABLE and GapDetector:
            try:
                from .gap_detector import detect_gaps_from_gathered
                gap_analysis = detect_gaps_from_gathered(
                    topic=question,
                    reference=reference,
                    regulatory=regulatory,
                    compliance=compliance,
                    project=analysis.get('project')
                )
                
                if gap_analysis.has_gaps:
                    analysis['gaps'] = [g.to_dict() for g in gap_analysis.gaps]
                    analysis['gap_summary'] = gap_analysis.summary()
                    analysis['coverage_score'] = gap_analysis.coverage_score
                    logger.warning(f"[GATHER-LIBRARY] Gap detection: {gap_analysis.summary()}")
                else:
                    analysis['gaps'] = []
                    analysis['gap_summary'] = "Full coverage"
                    analysis['coverage_score'] = 1.0
            except Exception as e:
                logger.warning(f"[GATHER-LIBRARY] Gap detection failed: {e}")
        
        return reference, regulatory, compliance
    
    # =========================================================================
    # ANALYSIS
    # =========================================================================
    
    def _detect_conflicts(self, reality, intent, configuration,
                         reference, regulatory, compliance) -> List[Conflict]:
        """
        Detect conflicts between truths.
        
        Looks for discrepancies where different truth sources disagree:
        - Reality vs Configuration (data doesn't match setup)
        - Reality vs Regulatory (data violates rules)
        - Configuration vs Reference (setup doesn't match best practice)
        - Intent vs Reality (what they want vs what they have)
        """
        conflicts = []
        
        def get_content_str(content) -> str:
            """Safely extract string content from Truth.content (may be str or dict)."""
            if isinstance(content, str):
                return content.lower()
            elif isinstance(content, dict):
                # For Reality truths, content is a dict with 'rows', 'columns', etc.
                # Use summary or data_context if available
                parts = []
                if content.get('sql'):
                    parts.append(str(content['sql']))
                if content.get('query_type'):
                    parts.append(str(content['query_type']))
                return ' '.join(parts).lower()
            return ""
        
        try:
            # Reality vs Regulatory conflicts
            for reg_truth in regulatory:
                for real_truth in reality:
                    # Check if regulatory requirement mentions something reality contradicts
                    reg_content = get_content_str(reg_truth.content)
                    real_content = get_content_str(real_truth.content)
                    
                    # Look for value mismatches (e.g., "rate must be X" vs "rate is Y")
                    if any(kw in reg_content for kw in ['must be', 'required', 'shall not exceed', 'minimum']):
                        if any(kw in real_content for kw in ['currently', 'actual', 'found', 'shows']):
                            conflicts.append(Conflict(
                                truth_a=reg_truth,
                                truth_b=real_truth,
                                conflict_type="regulatory_violation",
                                description=f"Potential compliance gap: {reg_truth.summary[:100]} vs {real_truth.summary[:100]}",
                                severity="medium"
                            ))
            
            # Configuration vs Reference conflicts  
            for ref_truth in reference:
                for config_truth in configuration:
                    ref_content = get_content_str(ref_truth.content)
                    config_content = get_content_str(config_truth.content)
                    
                    # Look for setup that doesn't match best practice
                    if any(kw in ref_content for kw in ['best practice', 'recommended', 'should be configured']):
                        if config_content and 'configured' in config_content:
                            conflicts.append(Conflict(
                                truth_a=ref_truth,
                                truth_b=config_truth,
                                conflict_type="best_practice_deviation",
                                description=f"Configuration may deviate from best practice",
                                severity="low"
                            ))
            
            # Intent vs Reality conflicts
            for intent_truth in intent:
                for real_truth in reality:
                    intent_content = get_content_str(intent_truth.content)
                    real_content = get_content_str(real_truth.content)
                    
                    # Look for gaps between what they want and what they have
                    if any(kw in intent_content for kw in ['want', 'need', 'require', 'goal']):
                        if any(kw in real_content for kw in ['currently', 'actual', 'no ', 'not ']):
                            conflicts.append(Conflict(
                                truth_a=intent_truth,
                                truth_b=real_truth,
                                conflict_type="intent_gap",
                                description=f"Gap between intent and reality",
                                severity="medium"
                            ))
            
            if conflicts:
                logger.info(f"[ENGINE-V2] Detected {len(conflicts)} conflicts")
                
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Conflict detection error: {e}")
        
        return conflicts
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """
        Run proactive analysis checks.
        
        Automatically flags potential issues without user asking:
        - Missing required configurations
        - Unusual data patterns
        - Approaching compliance deadlines
        """
        insights = []
        
        try:
            # If we have compliance results, surface them as insights
            if COMPLIANCE_ENGINE_AVAILABLE and self.customer_id:
                compliance_result = self._check_compliance([], [], [])
                if compliance_result and compliance_result.get('findings'):
                    for finding in compliance_result['findings'][:3]:  # Top 3
                        insights.append(Insight(
                            insight_type="compliance_finding",
                            description=finding.get('description', 'Compliance issue detected'),
                            severity=finding.get('severity', 'medium'),
                            source="compliance_engine",
                            recommendation=finding.get('recommendation', 'Review and remediate')
                        ))
            
            if insights:
                logger.info(f"[ENGINE-V2] Generated {len(insights)} proactive insights")
                
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Proactive check error: {e}")
        
        return insights
    
    def _check_compliance(self, reality, configuration,
                         regulatory) -> Optional[Dict]:
        """
        Check compliance against regulatory rules.
        
        Calls the ComplianceEngine to run rule-based checks against
        the project's data and configuration.
        """
        if not COMPLIANCE_ENGINE_AVAILABLE:
            logger.debug("[ENGINE-V2] ComplianceEngine not available")
            return None
        
        if not self.customer_id:
            logger.debug("[ENGINE-V2] No customer_id for compliance check")
            return None
        
        try:
            result = run_compliance_check(
                customer_id=self.customer_id,
                db_handler=self.structured_handler
            )
            
            if result:
                finding_count = len(result.get('findings', []))
                logger.info(f"[ENGINE-V2] Compliance check complete: {finding_count} findings")
                
            return result
            
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Compliance check error: {e}")
            return None
    
    # =========================================================================
    # FILTER MANAGEMENT
    # =========================================================================
    
    def confirm_filter(self, category: str, value: str):
        """Confirm a filter selection."""
        self.confirmed_facts[category] = value
        if self.sql_generator:
            self.sql_generator.confirmed_facts = self.confirmed_facts
        logger.info(f"[ENGINE-V2] Confirmed: {category}={value}")
    
    def clear_filters(self):
        """Clear all confirmed filters."""
        self.confirmed_facts = {}
        if self.sql_generator:
            self.sql_generator.confirmed_facts = {}
        logger.info("[ENGINE-V2] Filters cleared")
    
    def get_filter_options(self, category: str) -> List[Dict]:
        """Get available options for a filter category."""
        if category not in self.filter_candidates:
            return []
        
        candidates = self.filter_candidates[category]
        if not candidates:
            return []
        
        # Return unique values from first candidate
        best = candidates[0]
        values = best.get('value_distribution', {})
        return [{'id': v, 'label': v, 'count': c} for v, c in values.items()]
