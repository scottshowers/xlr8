# Phase 3: Synthesis

**Status:** NOT STARTED  
**Total Estimated Hours:** 12-16  
**Dependencies:** Phase 1 (SQL) and Phase 2 (Vector) substantially complete  
**Last Updated:** January 11, 2026

---

## Objective

Turn retrieved facts into consultative responses. This is where the LLM adds value - not in data retrieval (that's deterministic), but in assembling insights from multiple truths and presenting them like a consultant would.

---

## Background

### Current State

Current synthesis is basic pass-through:
- Get SQL results
- Get some vector context
- Send to LLM with "answer this question"

Problems:
- No structure to prompts
- Doesn't use Five Truths framework
- No gap highlighting
- Generic responses

### Target State

Synthesis that:
- Assembles all five truths into structured context
- Prompts LLM to reason across truths
- Highlights gaps and recommendations
- Produces responses that read like a consultant wrote them

---

## Component Overview

| # | Component | Hours | Description |
|---|-----------|-------|-------------|
| 3.1 | Five Truths Assembly | 3-4 | Structured context for LLM |
| 3.2 | Local LLM Prompt Engineering | 4-5 | Optimize for Mistral/DeepSeek |
| 3.3 | Gap Detection Logic | 3-4 | Identify and explain gaps |
| 3.4 | Consultative Response Patterns | 2-3 | Response templates and style |

---

## Component 3.1: Five Truths Assembly

**Goal:** Create structured input that gives LLM everything it needs.

### Truth Context Structure

```python
@dataclass
class TruthContext:
    """Assembled context for synthesis."""
    
    # The question
    question: str
    intent_type: str  # count, list, compare, etc.
    domain: str       # earnings, deductions, etc.
    
    # Reality Truth (from DuckDB)
    reality: RealityContext
    
    # Intent Truth (from ChromaDB - SOW/requirements)
    intent: IntentContext
    
    # Configuration Truth (from DuckDB - settings)
    configuration: ConfigurationContext
    
    # Reference Truth (from ChromaDB - best practices)
    reference: ReferenceContext
    
    # Regulatory Truth (from ChromaDB - compliance)
    regulatory: RegulatoryContext
    
    # Detected gaps
    gaps: List[Gap]
    
    # Citations collected
    citations: List[Citation]

@dataclass
class RealityContext:
    """What IS - actual data from customer."""
    sql_query: str
    row_count: int
    sample_data: List[Dict]  # First 10 rows
    column_names: List[str]
    aggregates: Dict[str, Any]  # count, sum, avg if relevant
    
@dataclass
class IntentContext:
    """What customer WANTS - from SOW/requirements."""
    relevant_requirements: List[str]
    source_documents: List[str]
    confidence: float

@dataclass
class ReferenceContext:
    """What's RECOMMENDED - from vendor docs/best practices."""
    relevant_guidance: List[str]
    source_documents: List[str]
    confidence: float

@dataclass
class RegulatoryContext:
    """What's REQUIRED - from compliance docs."""
    relevant_requirements: List[str]
    jurisdictions: List[str]  # federal, state:CA, etc.
    source_documents: List[str]
    confidence: float
```

### Assembly Process

```python
class TruthAssembler:
    """Assemble all five truths for synthesis."""
    
    def assemble(self, 
                query: str,
                sql_results: Dict,
                vector_results: Dict,
                gaps: List[Gap],
                citations: List[Citation]) -> TruthContext:
        """
        Combine all truth sources into structured context.
        """
        return TruthContext(
            question=query,
            intent_type=sql_results.get('intent', 'list'),
            domain=sql_results.get('domain', 'unknown'),
            
            reality=RealityContext(
                sql_query=sql_results.get('sql', ''),
                row_count=sql_results.get('row_count', 0),
                sample_data=sql_results.get('data', [])[:10],
                column_names=sql_results.get('columns', []),
                aggregates=sql_results.get('aggregates', {})
            ),
            
            intent=self._build_intent_context(vector_results),
            configuration=self._build_config_context(sql_results),
            reference=self._build_reference_context(vector_results),
            regulatory=self._build_regulatory_context(vector_results),
            
            gaps=gaps,
            citations=citations
        )
```

---

## Component 3.2: Local LLM Prompt Engineering

**Goal:** Optimize prompts for local LLMs (Mistral, DeepSeek).

### LLM Selection

| Model | Use Case | Strengths |
|-------|----------|-----------|
| DeepSeek | SQL explanation | Technical accuracy |
| Mistral | Synthesis | Natural language, reasoning |
| Claude API | Edge cases | Complex reasoning (fallback only) |

### Synthesis Prompt Template

```python
SYNTHESIS_PROMPT = """You are an HCM implementation consultant analyzing customer data.

## QUESTION
{question}

## WHAT THE DATA SHOWS (Reality)
Query executed: {sql_query}
Results: {row_count} rows
Sample data:
{sample_data}

## WHAT THE CUSTOMER WANTS (Intent)
{intent_context}

## BEST PRACTICES (Reference)
{reference_context}

## COMPLIANCE REQUIREMENTS (Regulatory)
{regulatory_context}

## GAPS DETECTED
{gaps_summary}

## YOUR TASK
Provide a consultative response that:
1. Directly answers the question using the data
2. Highlights any gaps between configuration and best practices
3. Notes compliance considerations if relevant
4. Suggests next steps if appropriate

Keep your response:
- Factual (cite specific numbers from the data)
- Consultative (like a trusted advisor)
- Actionable (if there are issues, suggest fixes)
- Concise (get to the point)

Response:"""
```

### Prompt Optimization for Local LLMs

```python
class LocalLLMPrompter:
    """Optimize prompts for local LLM constraints."""
    
    MAX_CONTEXT_TOKENS = 4096  # Mistral context window
    
    def optimize_prompt(self, context: TruthContext) -> str:
        """
        Build prompt that fits in context window.
        
        Priority order for truncation:
        1. Question (never truncate)
        2. Reality data (essential)
        3. Regulatory context (important)
        4. Reference context (helpful)
        5. Intent context (background)
        """
        prompt_parts = []
        
        # Always include question
        prompt_parts.append(f"QUESTION: {context.question}\n")
        
        # Always include reality (truncate rows if needed)
        reality_str = self._format_reality(context.reality, max_rows=10)
        prompt_parts.append(f"DATA:\n{reality_str}\n")
        
        # Add truths in priority order, tracking tokens
        remaining_tokens = self.MAX_CONTEXT_TOKENS - self._count_tokens(prompt_parts)
        
        for truth_section in [
            ('REGULATORY', context.regulatory),
            ('BEST PRACTICES', context.reference),
            ('CUSTOMER INTENT', context.intent)
        ]:
            section_str = self._format_truth(truth_section[1])
            section_tokens = self._count_tokens([section_str])
            
            if section_tokens < remaining_tokens:
                prompt_parts.append(f"{truth_section[0]}:\n{section_str}\n")
                remaining_tokens -= section_tokens
        
        # Add gaps
        if context.gaps:
            gaps_str = self._format_gaps(context.gaps)
            prompt_parts.append(f"GAPS:\n{gaps_str}\n")
        
        return self._assemble_prompt(prompt_parts)
```

### Response Quality Patterns

```python
# Ensure response includes key elements
RESPONSE_CHECKLIST = [
    'direct_answer',      # Actually answers the question
    'data_citation',      # References specific numbers
    'context_usage',      # Uses truth context
    'actionable_insight', # Suggests next steps if relevant
]

def validate_response(response: str, context: TruthContext) -> Dict:
    """Check response quality."""
    checks = {}
    
    # Direct answer check
    checks['direct_answer'] = any([
        context.question.lower().split()[0] in ['how', 'what', 'which']
        and any(c.isdigit() for c in response)  # Contains numbers
    ])
    
    # Data citation check
    if context.reality.row_count > 0:
        checks['data_citation'] = str(context.reality.row_count) in response
    
    # etc.
    
    return checks
```

---

## Component 3.3: Gap Detection Logic

**Goal:** Identify and explain meaningful gaps.

### Gap Types

```python
class GapType(Enum):
    CONFIG_VS_INTENT = "configured_vs_intended"      # Setup doesn't match SOW
    CONFIG_VS_REFERENCE = "configured_vs_best"       # Setup doesn't follow best practice
    CONFIG_VS_REGULATORY = "configured_vs_required"  # Setup may not be compliant
    MISSING_DATA = "missing_data"                    # Expected data not found
    INCOMPLETE_SETUP = "incomplete_setup"            # Partial configuration
```

### Gap Detection Rules

```python
GAP_RULES = {
    # If SOW mentions X but configuration doesn't have X → gap
    'intent_not_configured': {
        'condition': lambda intent, config: intent.mentioned and not config.present,
        'severity': 'HIGH',
        'recommendation': 'Customer requirement not configured. Verify scope.'
    },
    
    # If best practice says X but configuration uses Y → gap
    'not_best_practice': {
        'condition': lambda reference, config: reference.recommended != config.actual,
        'severity': 'MEDIUM',
        'recommendation': 'Current configuration differs from vendor recommendation.'
    },
    
    # If regulation requires X but configuration doesn't enforce → gap
    'compliance_risk': {
        'condition': lambda regulatory, config: regulatory.required and not config.enforced,
        'severity': 'HIGH',
        'recommendation': 'Configuration may not meet compliance requirements.'
    },
}
```

### Gap Explanation Generator

```python
class GapExplainer:
    """Generate human-readable gap explanations."""
    
    def explain_gap(self, gap: Gap, context: TruthContext) -> str:
        """
        Create consultative explanation of a gap.
        
        Example output:
        "The 401k match is configured at 3%, but the SOW specifies 4%. 
        This should be verified with the customer before go-live. 
        The standard UKG setup supports match rates up to 6%."
        """
        templates = {
            GapType.CONFIG_VS_INTENT: (
                "The {topic} is configured as {actual}, but the SOW specifies {expected}. "
                "This should be verified with the customer before go-live."
            ),
            GapType.CONFIG_VS_REFERENCE: (
                "The {topic} configuration ({actual}) differs from the recommended "
                "best practice ({expected}). Consider reviewing this setup."
            ),
            GapType.CONFIG_VS_REGULATORY: (
                "⚠️ The {topic} configuration may not meet {jurisdiction} requirements. "
                "{regulation_name} requires {expected}, but current setup shows {actual}."
            ),
        }
        
        template = templates.get(gap.gap_type)
        return template.format(**gap.details)
```

---

## Component 3.4: Consultative Response Patterns

**Goal:** Make responses read like a consultant wrote them.

### Response Structure

```
1. Direct Answer (1-2 sentences)
   - Actually answer the question with data
   
2. Supporting Detail (2-4 sentences)
   - Context from truths
   - Why this matters
   
3. Gaps/Recommendations (if any)
   - What's missing or concerning
   - Suggested actions
   
4. Citations (brief)
   - Source documents referenced
```

### Response Templates by Query Type

```python
RESPONSE_TEMPLATES = {
    'count': """
**{count:,} {entity}** match your criteria.

{breakdown_if_relevant}

{gap_section}
""",
    
    'list': """
Found **{count:,} {entity}** matching your query.

Here's a sample:
{sample_table}

{context_section}

{gap_section}
""",
    
    'compare': """
**Comparison: {dimension}**

{comparison_table}

**Key Findings:**
{findings}

{gap_section}
""",
    
    'gap_analysis': """
**Gap Analysis: {topic}**

| Truth | Status | Details |
|-------|--------|---------|
{truth_status_table}

**Recommended Actions:**
{recommendations}
"""
}
```

### Tone Guidelines

```python
TONE_RULES = {
    # DO
    'be_specific': "Use exact numbers: '127 employees' not 'many employees'",
    'be_direct': "Answer first, explain second",
    'be_helpful': "Suggest next steps when appropriate",
    'acknowledge_limits': "Say 'Based on the uploaded data...' when appropriate",
    
    # DON'T
    'no_hedging': "Avoid 'It appears that...' when data is clear",
    'no_jargon': "Avoid unexplained technical terms",
    'no_assumptions': "Don't assume context not in the data",
    'no_repetition': "Don't repeat the question back",
}
```

---

## Implementation Flow

```python
async def synthesize_response(
    query: str,
    sql_results: Dict,
    vector_results: Dict
) -> SynthesisResult:
    """
    Main synthesis pipeline.
    """
    # 1. Assemble truth context
    assembler = TruthAssembler()
    context = assembler.assemble(query, sql_results, vector_results)
    
    # 2. Detect gaps
    gap_detector = GapDetector()
    gaps = gap_detector.detect_gaps(context)
    context.gaps = gaps
    
    # 3. Build prompt
    prompter = LocalLLMPrompter()
    prompt = prompter.optimize_prompt(context)
    
    # 4. Call local LLM
    llm_response = await call_local_llm(prompt, model='mistral')
    
    # 5. Format response
    formatter = ResponseFormatter()
    formatted = formatter.format(
        llm_response, 
        context,
        template=RESPONSE_TEMPLATES[context.intent_type]
    )
    
    # 6. Validate response quality
    quality = validate_response(formatted, context)
    
    # 7. Add citations
    formatted_with_citations = add_citations(formatted, context.citations)
    
    return SynthesisResult(
        response=formatted_with_citations,
        context=context,
        quality_score=quality,
        model_used='mistral'
    )
```

---

## Integration Points

### From SQL Layer (Phase 1)

```python
# SQL layer provides:
{
    'sql': 'SELECT ...',
    'data': [...],
    'row_count': 127,
    'columns': ['name', 'state', ...],
    'intent': 'count',
    'domain': 'demographics'
}
```

### From Vector Layer (Phase 2)

```python
# Vector layer provides:
{
    'intent': [ChunkResult, ...],
    'reference': [ChunkResult, ...],
    'regulatory': [ChunkResult, ...],
    'citations': [Citation, ...]
}
```

### To Presentation Layer (Phase 4)

```python
# Synthesis provides:
{
    'response': 'Formatted consultative response...',
    'citations': [Citation, ...],
    'gaps': [Gap, ...],
    'quality_score': 0.92,
    'truths_used': ['reality', 'reference', 'regulatory']
}
```

---

## Testing Strategy

### Unit Tests
- Truth assembly completeness
- Prompt token counting
- Gap detection accuracy
- Response template rendering

### Integration Tests
- Full synthesis pipeline
- LLM response quality
- Citation accuracy

### Quality Validation
- A/B test response templates
- Measure answer accuracy
- Track user satisfaction

---

## Success Criteria

### Phase Complete When:
1. All five truths assembled into prompts
2. Local LLM prompts optimized for context window
3. Gap detection working for all gap types
4. Response templates produce consultative outputs
5. Quality validation passing

### Quality Gates:
- 90%+ responses directly answer the question
- Gap detection catches obvious mismatches
- Responses include relevant citations
- Sub-2s synthesis time with local LLM

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-11 | Initial detailed phase doc created |
