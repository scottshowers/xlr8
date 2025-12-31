"""
XLR8 Intelligence Engine - Truth Enricher (LLM Lookups)
========================================================

Enriches raw truths with LLM-extracted structured data.

This sits between gatherers and synthesizer:
    Gatherers → raw truths → TruthEnricher → enriched truths → Synthesizer

For semantic truths (ChromaDB chunks), extracts:
- regulatory: Rules, conditions, penalties, effective dates
- reference: Steps, settings, configuration guidance
- intent: Requirements, priorities, deliverables, stakeholders
- compliance: Controls, audit requirements, frameworks

For structured truths (DuckDB rows), minimal enrichment:
- reality: Pattern detection, anomaly flags
- configuration: Completeness checks, missing values

LLM Priority (via LLMOrchestrator):
1. Mistral:7b (local) - Fast, private, no cost
2. Claude API - Fallback for complex extractions

Deploy to: backend/utils/intelligence/truth_enricher.py
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .types import Truth, TruthType

logger = logging.getLogger(__name__)

# Try to import LLM orchestrator
try:
    from utils.llm_orchestrator import LLMOrchestrator
    LLM_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.llm_orchestrator import LLMOrchestrator
        LLM_AVAILABLE = True
    except ImportError:
        LLM_AVAILABLE = False
        logger.warning("[ENRICHER] LLMOrchestrator not available")


# =============================================================================
# EXTRACTION PROMPTS
# =============================================================================

REGULATORY_EXTRACTION_PROMPT = """Extract structured information from this regulatory text.

TEXT:
{text}

Return JSON with these fields (use null if not found):
{{
  "rule_id": "identifier if mentioned",
  "requirement": "what must be done",
  "condition": "when/who this applies to",
  "effective_date": "when it takes effect",
  "penalty": "consequences of non-compliance",
  "agency": "IRS, DOL, state, etc.",
  "law": "Secure 2.0, FLSA, etc.",
  "applies_to": ["list", "of", "affected", "entities"],
  "key_terms": ["important", "keywords"]
}}

Return ONLY valid JSON, no explanation."""


REFERENCE_EXTRACTION_PROMPT = """Extract structured information from this product/reference documentation.

TEXT:
{text}

Return JSON with these fields (use null if not found):
{{
  "topic": "what this is about",
  "product": "product name if mentioned",
  "action_type": "configuration, setup, troubleshooting, etc.",
  "steps": ["ordered", "list", "of", "steps"],
  "settings": {{"setting_name": "value or description"}},
  "prerequisites": ["what's", "needed", "first"],
  "warnings": ["important", "cautions"],
  "related_topics": ["related", "items"],
  "key_terms": ["important", "keywords"]
}}

Return ONLY valid JSON, no explanation."""


INTENT_EXTRACTION_PROMPT = """Extract structured information from this customer requirements/intent document.

TEXT:
{text}

Return JSON with these fields (use null if not found):
{{
  "requirement_type": "functional, technical, business, etc.",
  "priority": "high, medium, low if indicated",
  "deliverable": "what needs to be delivered",
  "stakeholder": "who requested or owns this",
  "deadline": "target date if mentioned",
  "acceptance_criteria": ["criteria", "for", "success"],
  "dependencies": ["what", "this", "depends", "on"],
  "constraints": ["limitations", "or", "restrictions"],
  "key_terms": ["important", "keywords"]
}}

Return ONLY valid JSON, no explanation."""


COMPLIANCE_EXTRACTION_PROMPT = """Extract structured information from this compliance/audit document.

TEXT:
{text}

Return JSON with these fields (use null if not found):
{{
  "control_id": "control identifier",
  "framework": "SOC 2, GDPR, HIPAA, etc.",
  "control_type": "preventive, detective, corrective",
  "requirement": "what must be in place",
  "evidence_needed": ["evidence", "for", "audit"],
  "frequency": "how often to verify",
  "owner": "responsible party",
  "risk_level": "high, medium, low",
  "key_terms": ["important", "keywords"]
}}

Return ONLY valid JSON, no explanation."""


# =============================================================================
# TRUTH ENRICHER
# =============================================================================

class TruthEnricher:
    """
    Enriches raw truths with LLM-extracted structured data.
    
    Uses local LLMs first (Mistral), falls back to Claude if needed.
    Caches extractions to avoid redundant LLM calls.
    """
    
    def __init__(self, project_id: str = None):
        """
        Initialize the enricher.
        
        Args:
            project_id: Project ID for metrics tracking
        """
        self.project_id = project_id
        self.orchestrator = None
        self._extraction_cache: Dict[str, Dict] = {}
        
        if LLM_AVAILABLE:
            try:
                self.orchestrator = LLMOrchestrator()
                logger.info("[ENRICHER] LLM orchestrator initialized")
            except Exception as e:
                logger.warning(f"[ENRICHER] LLM orchestrator failed: {e}")
    
    def enrich(self, truth: Truth) -> Truth:
        """
        Enrich a single truth with extracted structured data.
        
        Args:
            truth: Raw truth from gatherer
            
        Returns:
            Truth with added 'extracted' field in metadata
        """
        if not truth:
            return truth
        
        source_type = truth.source_type
        
        # Semantic truths need LLM extraction
        if source_type in ['regulatory', 'reference', 'intent', 'compliance']:
            return self._enrich_semantic_truth(truth)
        
        # Structured truths get light enrichment
        elif source_type in ['reality', 'configuration']:
            return self._enrich_structured_truth(truth)
        
        return truth
    
    def enrich_batch(self, truths: List[Truth]) -> List[Truth]:
        """
        Enrich a batch of truths.
        
        Args:
            truths: List of raw truths
            
        Returns:
            List of enriched truths
        """
        return [self.enrich(t) for t in truths]
    
    def _enrich_semantic_truth(self, truth: Truth) -> Truth:
        """Enrich semantic (ChromaDB) truth with LLM extraction."""
        # Get text content
        content = truth.content
        if isinstance(content, dict):
            text = content.get('text', '')
        else:
            text = str(content)
        
        if not text or len(text) < 50:
            return truth
        
        # Check cache
        cache_key = f"{truth.source_type}:{hash(text[:500])}"
        if cache_key in self._extraction_cache:
            truth.metadata['extracted'] = self._extraction_cache[cache_key]
            truth.metadata['extraction_source'] = 'cache'
            return truth
        
        # Select prompt based on truth type
        prompt_map = {
            'regulatory': REGULATORY_EXTRACTION_PROMPT,
            'reference': REFERENCE_EXTRACTION_PROMPT,
            'intent': INTENT_EXTRACTION_PROMPT,
            'compliance': COMPLIANCE_EXTRACTION_PROMPT,
        }
        
        prompt_template = prompt_map.get(truth.source_type)
        if not prompt_template:
            return truth
        
        # Extract using LLM
        extracted = self._extract_with_llm(text, prompt_template, truth.source_type)
        
        if extracted:
            # Cache the extraction
            self._extraction_cache[cache_key] = extracted
            
            # Add to truth metadata
            truth.metadata['extracted'] = extracted
            truth.metadata['extraction_source'] = 'llm'
            
            # Boost confidence if we got good extraction
            if extracted.get('key_terms'):
                truth.confidence = min(1.0, truth.confidence + 0.05)
        
        return truth
    
    def _enrich_structured_truth(self, truth: Truth) -> Truth:
        """Enrich structured (DuckDB) truth with pattern analysis."""
        content = truth.content
        if not isinstance(content, dict):
            return truth
        
        rows = content.get('rows', [])
        if not rows:
            return truth
        
        # Light enrichment - no LLM needed
        enrichment = {
            'row_count': len(rows),
            'columns': content.get('columns', []),
            'has_nulls': self._check_for_nulls(rows),
            'unique_values': self._count_unique_first_column(rows),
        }
        
        # For configuration tables, check completeness
        if truth.source_type == 'configuration':
            enrichment['completeness'] = self._assess_completeness(rows)
        
        truth.metadata['extracted'] = enrichment
        truth.metadata['extraction_source'] = 'analysis'
        
        return truth
    
    def _extract_with_llm(self, text: str, prompt_template: str, 
                         truth_type: str) -> Optional[Dict]:
        """Use LLM to extract structured data from text."""
        if not self.orchestrator:
            return None
        
        # Truncate very long text
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        prompt = prompt_template.format(text=text)
        
        try:
            # Use Mistral for extraction (local first)
            result, success = self.orchestrator._call_ollama(
                model="mistral:7b",
                prompt=prompt,
                system_prompt="You are a precise data extraction assistant. Return only valid JSON.",
                project_id=self.project_id,
                processor=f"truth_enricher_{truth_type}"
            )
            
            if success and result:
                # Parse JSON from response
                extracted = self._parse_json_response(result)
                if extracted:
                    logger.debug(f"[ENRICHER] Extracted {truth_type}: {list(extracted.keys())}")
                    return extracted
            
            # If local fails, try Claude for complex cases
            if not success or not result:
                result = self._call_claude_extraction(prompt, truth_type)
                if result:
                    return self._parse_json_response(result)
                    
        except Exception as e:
            logger.warning(f"[ENRICHER] Extraction failed for {truth_type}: {e}")
        
        return None
    
    def _call_claude_extraction(self, prompt: str, truth_type: str) -> Optional[str]:
        """Fallback to Claude for complex extractions."""
        if not self.orchestrator or not self.orchestrator.claude_api_key:
            return None
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.orchestrator.claude_api_key)
            
            response = client.messages.create(
                model=self.orchestrator.claude_model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if response.content:
                logger.debug(f"[ENRICHER] Claude extraction for {truth_type}")
                return response.content[0].text
                
        except Exception as e:
            logger.warning(f"[ENRICHER] Claude extraction failed: {e}")
        
        return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        if not response:
            return None
        
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from response
        try:
            # Look for JSON block
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        
        return None
    
    def _check_for_nulls(self, rows: List[Dict]) -> bool:
        """Check if any rows have null values."""
        for row in rows[:10]:  # Sample first 10
            for v in row.values():
                if v is None or v == '' or v == 'NULL':
                    return True
        return False
    
    def _count_unique_first_column(self, rows: List[Dict]) -> int:
        """Count unique values in first column."""
        if not rows:
            return 0
        first_col = list(rows[0].keys())[0]
        values = set(row.get(first_col) for row in rows)
        return len(values)
    
    def _assess_completeness(self, rows: List[Dict]) -> Dict:
        """Assess completeness of configuration data."""
        if not rows:
            return {'complete': False, 'missing_fields': []}
        
        # Count nulls per column
        columns = list(rows[0].keys())
        null_counts = {col: 0 for col in columns}
        
        for row in rows:
            for col in columns:
                val = row.get(col)
                if val is None or val == '' or val == 'NULL':
                    null_counts[col] += 1
        
        # Flag columns with >50% nulls
        total = len(rows)
        incomplete_cols = [col for col, count in null_counts.items() 
                         if count > total * 0.5]
        
        return {
            'complete': len(incomplete_cols) == 0,
            'missing_fields': incomplete_cols,
            'total_rows': total
        }
    
    def clear_cache(self):
        """Clear extraction cache."""
        self._extraction_cache.clear()
        logger.info("[ENRICHER] Cache cleared")
