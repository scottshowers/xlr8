# Phase 2: Vector Retrieval

**Status:** IN PROGRESS  
**Total Estimated Hours:** 20-25  
**Dependencies:** Phase 1 (SQL Evolutions) core complete  
**Last Updated:** January 12, 2026

---

## Objective

Make ChromaDB useful for the Five Truths framework. Currently ChromaDB stores documents but retrieval is basic similarity search. We need domain-aware, query-typed retrieval that understands document provenance.

---

## Background

### Current State

ChromaDB stores:
- Uploaded PDFs and documents (chunked)
- Standards documents (regulatory, best practices)
- SOW/requirements documents (customer intent)

Current retrieval:
- Basic similarity search
- ✅ Domain tagging at upload (Phase 2B.1 COMPLETE)
- No source type differentiation in queries
- No relevance scoring beyond similarity

### Target State

ChromaDB becomes the source of truth for:
- **Intent** - What customer wants (SOW, requirements)
- **Reference** - What vendor recommends (best practices)
- **Regulatory** - What's required (IRS, state laws)
- **Compliance** - Internal policies

Each query pulls relevant context from the right truth(s).

---

## Component Overview

| # | Component | Hours | Status | Description |
|---|-----------|-------|--------|-------------|
| 2B.1 | Domain-Tagged Chunks | 3-4 | ✅ DONE | Tag chunks with truth type at upload |
| 2B.2 | Query-Aware Vector Search | 4-5 | ✅ DONE | Route queries to appropriate truths |
| 2B.3 | Source Typing & Prioritization | 2-3 | ✅ DONE | Weight sources by reliability |
| 2B.4 | Relevance Scoring & Filtering | 3-4 | ✅ DONE | Beyond similarity - contextual relevance |
| 2B.5 | Citation Tracking | 2-3 | ✅ DONE | Track provenance for responses |
| 2B.6 | Gap Detection Queries | 4-5 | ✅ DONE | Find missing truth coverage |

---

## Component 2B.1: Domain-Tagged Chunks ✅ COMPLETE

**Completed:** January 12, 2026

**Implementation:**
- File: `backend/utils/intelligence/chunk_classifier.py`
- Integrated into: `utils/rag_handler.py`
- Approach: Pattern-based classification (deterministic, no LLM)

**Chunk Metadata Now Includes:**
```python
{
    "project": "tea1000",
    "filename": "UKG_Best_Practices.pdf",
    "chunk_index": 5,
    "page": 2,
    # NEW FIELDS (Phase 2B.1)
    "truth_type": "reference",          # intent|reference|regulatory|compliance
    "domain": "earnings",               # demographics|earnings|deductions|taxes|time|organization|etc
    "source_authority": "vendor",       # government|vendor|industry|customer|internal
    "classification_confidence": 0.85   # How confident the classification is
}
```

**Test Results:**
| Test Case | truth_type | domain | authority | confidence |
|-----------|------------|--------|-----------|------------|
| IRS Pub 15 | regulatory ✅ | taxes ✅ | government ✅ | 0.77 |
| UKG Best Practice | reference ✅ | earnings ✅ | vendor ✅ | 0.90 |
| Customer SOW | intent ✅ | deductions ✅ | customer ✅ | 0.79 |
| Internal Policy | compliance ✅ | time ✅ | internal ✅ | 0.74 |

### Original Design (preserved for reference)

**Goal:** Every chunk in ChromaDB knows what truth it represents.

### Current Chunk Metadata
```python
{
    "project": "tea1000",
    "filename": "UKG_Best_Practices.pdf",
    "chunk_index": 5,
    "page": 2
}
```

### Enhanced Chunk Metadata
```python
{
    "project": "tea1000",
    "filename": "UKG_Best_Practices.pdf",
    "chunk_index": 5,
    "page": 2,
    # NEW FIELDS
    "truth_type": "reference",          # intent|reference|regulatory|compliance
    "domain": "deductions",              # earnings|deductions|taxes|etc.
    "source_authority": "vendor",        # vendor|government|customer|internal
    "effective_date": "2025-01-01",      # When this guidance applies
    "jurisdiction": "federal",           # federal|state:CA|country:US|global
    "confidence": 0.95                   # Classification confidence
}
```

### Truth Type Classification

At upload time, classify documents:

```python
TRUTH_TYPE_PATTERNS = {
    'intent': {
        'filenames': ['sow', 'requirements', 'scope', 'project_plan', 'contract'],
        'content': ['customer wants', 'shall implement', 'requirement:', 'deliverable'],
    },
    'reference': {
        'filenames': ['best_practice', 'guide', 'manual', 'documentation', 'reference'],
        'content': ['recommended', 'best practice', 'should configure', 'standard approach'],
    },
    'regulatory': {
        'filenames': ['irs', 'dol', 'flsa', 'regulation', 'law', 'code', 'statute'],
        'content': ['must comply', 'required by law', 'penalty', 'federal requirement'],
    },
    'compliance': {
        'filenames': ['policy', 'procedure', 'internal', 'company_policy', 'handbook'],
        'content': ['company policy', 'internal requirement', 'our standard', 'approved by'],
    }
}
```

### Domain Classification

Map content to HCM domains:

```python
DOMAIN_KEYWORDS = {
    'demographics': ['employee', 'worker', 'hire', 'terminate', 'status'],
    'earnings': ['pay', 'wage', 'salary', 'compensation', 'earning code'],
    'deductions': ['deduction', 'benefit', '401k', 'insurance', 'hsa'],
    'taxes': ['tax', 'withholding', 'w-2', 'sui', 'futa', 'fica'],
    'time': ['time', 'attendance', 'pto', 'accrual', 'schedule'],
    'organization': ['company', 'department', 'location', 'org', 'hierarchy'],
}
```

### Implementation

File: `/backend/utils/intelligence/chunk_classifier.py`

```python
class ChunkClassifier:
    """Classify chunks for Five Truths metadata."""
    
    def classify_document(self, filename: str, content: str) -> Dict:
        """
        Classify an entire document.
        
        Returns:
            {'truth_type': str, 'domain': str, 'source_authority': str, ...}
        """
        truth_type = self._classify_truth_type(filename, content)
        domain = self._classify_domain(content)
        authority = self._classify_authority(filename, content)
        
        return {
            'truth_type': truth_type,
            'domain': domain,
            'source_authority': authority,
            'confidence': self._calculate_confidence(...)
        }
    
    def _classify_truth_type(self, filename: str, content: str) -> str:
        """Determine which truth this document represents."""
        filename_lower = filename.lower()
        content_lower = content.lower()[:5000]  # First 5k chars
        
        scores = {}
        for truth_type, patterns in TRUTH_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns['filenames']:
                if pattern in filename_lower:
                    score += 2
            for pattern in patterns['content']:
                if pattern in content_lower:
                    score += 1
            scores[truth_type] = score
        
        if max(scores.values()) == 0:
            return 'reference'  # Default
        
        return max(scores, key=scores.get)
```

---

## Component 2B.2: Query-Aware Vector Search ✅ COMPLETE

**Completed:** January 12, 2026

**Implementation:**
- File: `backend/utils/intelligence/truth_router.py`
- Integrated into: `backend/utils/intelligence/engine.py` (`_gather_reference_library()`)
- Approach: Pattern-based query routing (deterministic, no LLM)

**Query Categories:**
| Category | Patterns | Truths Queried |
|----------|----------|----------------|
| regulatory_required | "required", "must", "IRS", "compliance" | regulatory, compliance |
| best_practice | "best practice", "recommend", "how to" | reference, regulatory |
| customer_intent | "customer wants", "SOW", "scope" | intent |
| gap_analysis | "gap", "missing", "compare" | reference, intent, regulatory |
| implementation | "how to", "configure", "set up" | reference |
| policy | "policy", "procedure", "control" | compliance, intent |
| default | (no pattern match) | all truths |

**Domain Detection:**
Automatically detects HCM domain from query: demographics, earnings, deductions, taxes, time, organization

**Test Results:**
| Query | Category | Domain | Truths |
|-------|----------|--------|--------|
| "What tax withholding is required by the IRS?" | regulatory_required | taxes | regulatory, compliance |
| "Best practice for configuring earnings codes" | best_practice | earnings | reference, regulatory |
| "What did customer want in SOW for deductions?" | customer_intent | deductions | intent |
| "What's missing from time tracking config?" | gap_analysis | time | reference, intent, regulatory |
| "How many active employees in Texas?" | default | demographics | all |

**Original Design (preserved for reference):**

**Goal:** Route queries to appropriate truth types based on what's being asked.

### Query Type → Truth Mapping

| Query Pattern | Primary Truths | Secondary |
|--------------|----------------|-----------|
| "What's configured?" | Configuration | Reference |
| "What's required?" | Regulatory | Compliance |
| "Best practice for X" | Reference | Regulatory |
| "Customer wants X" | Intent | - |
| "Why is X set up this way?" | All | - |

### Implementation

File: `/backend/utils/intelligence/truth_router.py`

```python
class TruthRouter:
    """Route queries to appropriate truth sources."""
    
    QUERY_PATTERNS = {
        'regulatory_required': {
            'patterns': ['required', 'must', 'mandatory', 'compliance', 'law'],
            'truths': ['regulatory', 'compliance'],
            'priority': [1.0, 0.8]
        },
        'best_practice': {
            'patterns': ['best practice', 'recommend', 'should', 'standard'],
            'truths': ['reference', 'regulatory'],
            'priority': [1.0, 0.6]
        },
        'customer_intent': {
            'patterns': ['customer wants', 'sow', 'requirement', 'scope'],
            'truths': ['intent'],
            'priority': [1.0]
        },
        'gap_analysis': {
            'patterns': ['gap', 'missing', 'not configured', 'difference'],
            'truths': ['reference', 'intent', 'regulatory'],
            'priority': [1.0, 0.9, 0.8]
        }
    }
    
    def route_query(self, query: str, domain: str = None) -> List[TruthQuery]:
        """
        Determine which truths to query and with what priority.
        
        Returns:
            List of TruthQuery objects with truth_type and weight
        """
        query_lower = query.lower()
        
        for pattern_type, config in self.QUERY_PATTERNS.items():
            for pattern in config['patterns']:
                if pattern in query_lower:
                    return [
                        TruthQuery(truth_type=t, weight=w, domain=domain)
                        for t, w in zip(config['truths'], config['priority'])
                    ]
        
        # Default: search all truths with equal weight
        return [
            TruthQuery(truth_type=t, weight=1.0, domain=domain)
            for t in ['reference', 'regulatory', 'intent', 'compliance']
        ]
```

---

## Component 2B.3: Source Typing & Prioritization ✅ COMPLETE

**Completed:** January 12, 2026

**Implementation:**
- File: `backend/utils/intelligence/source_prioritizer.py`
- Integrated into: `backend/utils/intelligence/engine.py` (`_gather_reference_library()`)
- Approach: Query-type specific weight matrices (deterministic, no LLM)

**Authority Hierarchy (base):**
```
government (IRS, DOL) > vendor (UKG docs) > industry (SHRM) > customer (SOW) > internal (notes)
```

**Weight Matrix by Query Type:**
| Source Authority | regulatory_required | best_practice | customer_intent | default |
|------------------|--------------------:|---------------:|----------------:|--------:|
| Government | 1.0 | 0.6 | 0.3 | 0.9 |
| Vendor | 0.6 | 1.0 | 0.5 | 0.85 |
| Industry | 0.5 | 0.8 | 0.4 | 0.7 |
| Customer | 0.2 | 0.3 | 1.0 | 0.6 |
| Internal | 0.3 | 0.4 | 0.6 | 0.5 |

**Test Results:**
| Query Type | Winner (despite lower similarity) |
|------------|-----------------------------------|
| regulatory_required | IRS Pub 15 (government) beats UKG Guide (vendor) |
| best_practice | UKG Best Practices (vendor) beats IRS Pub 15 (government) |
| customer_intent | Customer SOW beats UKG Docs (vendor) |

**Scoring Formula:**
```python
final_score = (
    similarity * 0.50 +      # Base ChromaDB similarity
    authority * 0.30 +       # Source authority weight
    domain_match * 0.15 +    # Domain alignment bonus
    routing_weight * 0.05    # TruthRouter weight
)
```

**Original Design (preserved for reference):**

**Goal:** Weight sources by reliability and authority.

### Authority Hierarchy

```
government (IRS, DOL) > vendor (UKG docs) > industry (SHRM) > customer (SOW) > internal (notes)
```

### Source Weight Matrix

| Source Type | Regulatory Query | Reference Query | Intent Query |
|-------------|-----------------|-----------------|--------------|
| Government | 1.0 | 0.6 | 0.3 |
| Vendor | 0.7 | 1.0 | 0.5 |
| Industry | 0.5 | 0.8 | 0.4 |
| Customer | 0.2 | 0.3 | 1.0 |
| Internal | 0.3 | 0.4 | 0.6 |

### Implementation

```python
class SourcePrioritizer:
    """Weight results by source authority."""
    
    def prioritize_results(self, 
                          results: List[ChunkResult], 
                          query_type: str) -> List[ChunkResult]:
        """
        Re-rank results by source authority for query type.
        """
        weights = SOURCE_WEIGHTS[query_type]
        
        for result in results:
            authority = result.metadata.get('source_authority', 'internal')
            authority_weight = weights.get(authority, 0.5)
            
            # Combine similarity with authority
            result.final_score = (
                result.similarity_score * 0.6 + 
                authority_weight * 0.4
            )
        
        return sorted(results, key=lambda r: r.final_score, reverse=True)
```

---

## Component 2B.4: Relevance Scoring & Filtering ✅ COMPLETE

**Completed:** January 12, 2026

**Implementation:**
- File: `backend/utils/intelligence/relevance_scorer.py`
- Integrated into: `backend/utils/intelligence/engine.py` (`_gather_reference_library()`)
- Supersedes 2B.3 SourcePrioritizer (includes all its logic plus more)

**Scoring Factors (5 factors):**
| Factor | Weight | Description |
|--------|--------|-------------|
| Similarity | 0.45 | Base ChromaDB embedding distance |
| Authority | 0.25 | Source authority per query type (from 2B.3) |
| Domain Match | 0.15 | Chunk domain matches query domain |
| Recency | 0.10 | More recent documents score higher |
| Jurisdiction | 0.05 | State/federal alignment |

**Recency Scoring:**
| Age | Score |
|-----|-------|
| Last 6 months | 1.0 |
| Last 1 year | 0.9 |
| Last 2 years | 0.8 |
| Last 3 years | 0.7 |
| Older | 0.6 |
| No date | 0.7 (neutral) |

**Jurisdiction Scoring:**
| Match Type | Score |
|------------|-------|
| Exact match (CA→CA) | 1.0 |
| Federal matches any | 0.9 |
| State matches federal | 0.8 |
| Different states | 0.5 |

**Filtering:**
- Minimum threshold: 0.5 (configurable)
- Maximum results: 10 (configurable)
- Low-quality results automatically excluded

**Test Results:**
| Test | Winner |
|------|--------|
| Recency | New IRS Doc (2025) beats Old IRS Doc (2020) |
| Jurisdiction | CA State Law beats TX State Law for CA query |
| Filtering | 3 results → 2 after threshold filter |
| Combined | Perfect Match (0.95) > Good Match (0.80) > Weak Match (0.59) |

**Original Design (preserved for reference):**

**Goal:** Go beyond embedding similarity to contextual relevance.

### Relevance Factors

1. **Similarity Score** - Base embedding distance (0.6 weight)
2. **Domain Match** - Chunk domain matches query domain (0.15 weight)
3. **Source Authority** - Higher for authoritative sources (0.1 weight)
4. **Recency** - More recent documents preferred (0.1 weight)
5. **Jurisdiction Match** - State/federal alignment (0.05 weight)

### Minimum Relevance Threshold

```python
MINIMUM_RELEVANCE = 0.65  # Below this, don't include in results

def filter_results(results: List[ChunkResult]) -> List[ChunkResult]:
    """Remove low-relevance results."""
    return [r for r in results if r.final_score >= MINIMUM_RELEVANCE]
```

### Implementation

```python
class RelevanceScorer:
    """Multi-factor relevance scoring."""
    
    def score_chunk(self, 
                   chunk: ChunkResult, 
                   query_context: QueryContext) -> float:
        """
        Calculate composite relevance score.
        """
        scores = {}
        
        # Factor 1: Embedding similarity (from ChromaDB)
        scores['similarity'] = chunk.distance_score
        
        # Factor 2: Domain match
        scores['domain'] = 1.0 if chunk.domain == query_context.domain else 0.5
        
        # Factor 3: Source authority
        scores['authority'] = self._authority_score(
            chunk.source_authority, 
            query_context.query_type
        )
        
        # Factor 4: Recency
        scores['recency'] = self._recency_score(chunk.effective_date)
        
        # Factor 5: Jurisdiction
        scores['jurisdiction'] = self._jurisdiction_score(
            chunk.jurisdiction,
            query_context.jurisdiction
        )
        
        # Weighted combination
        weights = {'similarity': 0.6, 'domain': 0.15, 'authority': 0.1, 
                   'recency': 0.1, 'jurisdiction': 0.05}
        
        return sum(scores[k] * weights[k] for k in scores)
```

---

## Component 2B.5: Citation Tracking ✅ COMPLETE

**Completed:** January 12, 2026

**Implementation:**
- File: `backend/utils/intelligence/citation_tracker.py`
- Integrated into: `backend/utils/intelligence/engine.py` (`_gather_reference_library()`)
- Added `citations` field to `SynthesizedAnswer` in `types.py`

**Citation Structure:**
```python
Citation(
    source_document="IRS_Pub_15.pdf",
    source_type="regulatory",
    source_authority="government",
    page_number=5,
    section="Withholding Requirements",
    excerpt="You must withhold taxes...",
    relevance_score=0.85,
    domain="taxes",
    jurisdiction="federal"
)
```

**Display Formats:**
| Style | Output |
|-------|--------|
| brief | `[IRS_Pub_15.pdf, p.5]` |
| full | `[IRS_Pub_15.pdf, p.5] (government)` |
| academic | `Government. IRS_Pub_15.pdf. Page 5.` |

**Features:**
- Automatic deduplication (same doc+chunk only cited once)
- Top-N citation retrieval by relevance score
- Filter by truth type or authority
- Bibliography formatting
- Inline citation formatting
- JSON serialization for API responses

**Integration:**
- Citations automatically collected during `_gather_reference_library()`
- Stored in `analysis['citations']` as list of dicts
- Available in `SynthesizedAnswer.citations` field

**Original Design (preserved for reference):**

**Goal:** Track provenance so responses can cite sources.

### Citation Structure

```python
@dataclass
class Citation:
    """A citation to source material."""
    source_document: str        # Original filename
    page_number: int            # Page in original
    chunk_text: str             # Relevant excerpt
    truth_type: str             # Which truth
    authority: str              # Source authority
    relevance_score: float      # How relevant
    
    def to_display(self) -> str:
        """Format for response display."""
        return f"[{self.source_document}, p.{self.page_number}]"
```

### Citation Collection

```python
class CitationCollector:
    """Collect and deduplicate citations during retrieval."""
    
    def __init__(self):
        self.citations = []
        self.seen_chunks = set()
    
    def add_from_result(self, result: ChunkResult):
        """Add citation from retrieval result."""
        chunk_id = f"{result.document}:{result.chunk_index}"
        if chunk_id in self.seen_chunks:
            return
        
        self.seen_chunks.add(chunk_id)
        self.citations.append(Citation(
            source_document=result.document,
            page_number=result.page,
            chunk_text=result.text[:200],  # Preview
            truth_type=result.truth_type,
            authority=result.source_authority,
            relevance_score=result.final_score
        ))
    
    def get_top_citations(self, n: int = 5) -> List[Citation]:
        """Get top N citations by relevance."""
        sorted_citations = sorted(
            self.citations, 
            key=lambda c: c.relevance_score, 
            reverse=True
        )
        return sorted_citations[:n]
```

---

## Component 2B.6: Gap Detection Queries ✅ COMPLETE

**Completed:** January 12, 2026

**Implementation:**
- File: `backend/utils/intelligence/gap_detector.py`
- Integrated into: `backend/utils/intelligence/engine.py` (`_gather_reference_library()`)
- Archived: Old HCM-specific `gap_detection_engine.py` moved to archive

**Gap Types Detected:**
| Gap Type | Severity | Description |
|----------|----------|-------------|
| Regulatory | high | No compliance/regulatory guidance found |
| Compliance | high | No internal policy documentation found |
| Intent | medium | No SOW/requirements found |
| Reference | low | No best practice documentation found |

**Coverage Threshold:** 0.5 (configurable)
- Truths with confidence below threshold count as "missing"

**GapAnalysis Output:**
```python
GapAnalysis(
    topic="401k matching",
    project="tea1000",
    gaps=[Gap(truth_type="regulatory", severity="high", ...)],
    covered_truths=["reference", "intent", "compliance"],
    coverage_score=0.75
)
```

**Test Results:**
| Scenario | Coverage | Gaps |
|----------|----------|------|
| All truths present (>0.5) | 100% | 0 |
| Missing regulatory | 75% | 1 (high) |
| Low confidence reference + compliance | 50% | 2 |
| No documentation | 0% | 4 |

**Integration:**
- Gap analysis runs automatically in `_gather_reference_library()`
- Results stored in `analysis['gaps']`, `analysis['gap_summary']`, `analysis['coverage_score']`
- Product-agnostic - no hardcoded domains

**Original Design (preserved for reference):**

**Goal:** Identify missing Five Truths coverage for a topic.

### Gap Types

1. **Intent Gap** - No SOW requirements for configured feature
2. **Reference Gap** - No best practice guidance for setup
3. **Regulatory Gap** - No compliance check for required item
4. **Configuration Gap** - Required item not set up

### Gap Detection Query

```python
class GapDetector:
    """Detect gaps in Five Truths coverage."""
    
    def detect_gaps(self, topic: str, project: str) -> List[Gap]:
        """
        Find missing truth coverage for a topic.
        
        Example: detect_gaps("401k matching", "tea1000")
        Returns gaps like:
        - No regulatory guidance for 401k match limits
        - No SOW requirement specifying match percentage
        """
        gaps = []
        
        # Check each truth type
        for truth_type in ['intent', 'reference', 'regulatory', 'compliance']:
            results = self.search_truth(topic, truth_type, project)
            
            if not results or results[0].relevance_score < 0.5:
                gaps.append(Gap(
                    truth_type=truth_type,
                    topic=topic,
                    severity=self._calculate_severity(truth_type, topic),
                    recommendation=self._get_recommendation(truth_type, topic)
                ))
        
        return gaps
    
    def _calculate_severity(self, truth_type: str, topic: str) -> str:
        """Determine gap severity."""
        if truth_type == 'regulatory':
            return 'HIGH'  # Missing compliance guidance is serious
        elif truth_type == 'intent':
            return 'MEDIUM'  # Should validate with customer
        else:
            return 'LOW'  # Nice to have
```

---

## Integration Points

### With SQL Layer (Phase 1)

```python
# After SQL returns Reality data, enrich with other truths
reality_data = execute_sql(assembled_query)
vector_context = retrieve_truths(query, domain)

combined = {
    'reality': reality_data,
    'reference': vector_context.get('reference'),
    'regulatory': vector_context.get('regulatory'),
    'intent': vector_context.get('intent'),
    'gaps': vector_context.get('gaps')
}
```

### With Synthesis Layer (Phase 3)

```python
# Pass all truths to synthesis
response = synthesize(
    question=query,
    reality=sql_results,
    reference_context=vector_context['reference'],
    regulatory_context=vector_context['regulatory'],
    citations=citation_collector.get_top_citations()
)
```

---

## Testing Strategy

### Unit Tests
- Chunk classification accuracy
- Query routing correctness
- Relevance scoring consistency
- Citation deduplication

### Integration Tests
- Full retrieval pipeline
- Multi-truth queries
- Gap detection accuracy

### Manual Validation
- Upload test documents of each truth type
- Verify classification
- Query and check relevance

---

## Success Criteria

### Phase Complete When:
1. All documents classified with truth metadata
2. Query routing working for all truth types
3. Citations tracked and displayed
4. Gap detection operational
5. Integration with SQL layer complete

### Quality Gates:
- 90%+ truth type classification accuracy
- Sub-500ms vector retrieval
- Relevant results in top 5 for all test queries
- Citation accuracy verified

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-11 | Initial detailed phase doc created |
