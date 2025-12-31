"""
XLR8 Intelligence Engine - Intent Parser
=========================================

Parses SOW/requirements documents at upload time to extract
structured requirements that can be tracked and queried.

This is different from TruthEnricher:
- TruthEnricher: Enriches chunks at query time
- IntentParser: Extracts full requirements at upload time

Output:
- List of ParsedRequirement objects
- Can be stored in DuckDB for tracking
- Enables requirement coverage analysis

Usage:
    parser = IntentParser(project_id="xxx")
    requirements = parser.parse_document(text, filename="sow.pdf")
    # Returns list of ParsedRequirement with:
    #   - requirement_id
    #   - text
    #   - category (functional, technical, integration, etc.)
    #   - priority
    #   - deliverable
    #   - acceptance_criteria
    #   - status (pending, in_progress, complete)

Deploy to: backend/utils/intelligence/intent_parser.py
"""

import json
import re
import hashlib
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

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
        logger.warning("[INTENT-PARSER] LLMOrchestrator not available")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ParsedRequirement:
    """A structured requirement extracted from an intent document."""
    requirement_id: str
    text: str
    category: str  # functional, technical, integration, data, reporting, security
    priority: str  # high, medium, low
    source_file: str
    source_page: Optional[str] = None
    source_section: Optional[str] = None
    
    # Extracted details
    deliverable: Optional[str] = None
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    stakeholder: Optional[str] = None
    deadline: Optional[str] = None
    
    # Tracking
    status: str = "pending"  # pending, in_progress, complete, blocked
    coverage_score: float = 0.0  # 0-1, how well covered by reality/config
    notes: str = ""
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ParsedRequirement':
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# EXTRACTION PROMPTS
# =============================================================================

REQUIREMENTS_EXTRACTION_PROMPT = """You are extracting requirements from a Statement of Work (SOW) or requirements document.

DOCUMENT TEXT:
{text}

Extract ALL requirements mentioned. For each requirement, identify:
1. The specific requirement text
2. Category: functional, technical, integration, data, reporting, security, or other
3. Priority: high, medium, low (based on language like "must", "critical", "should", "nice to have")
4. Deliverable: what needs to be produced/configured
5. Acceptance criteria: how to verify it's complete
6. Dependencies: what it depends on
7. Stakeholder: who requested or owns it
8. Deadline: any mentioned dates

Return a JSON array of requirements:
[
  {{
    "text": "exact requirement text or close paraphrase",
    "category": "functional|technical|integration|data|reporting|security|other",
    "priority": "high|medium|low",
    "deliverable": "what to deliver",
    "acceptance_criteria": ["criterion 1", "criterion 2"],
    "dependencies": ["dependency 1"],
    "stakeholder": "who owns this",
    "deadline": "date if mentioned"
  }}
]

Be thorough - extract ALL requirements, even implied ones.
Return ONLY the JSON array, no explanation."""


SECTION_DETECTION_PROMPT = """Identify the sections in this document that contain requirements.

DOCUMENT TEXT:
{text}

List the section names/headers that contain requirements, deliverables, or scope items.
Return a JSON array of section names:
["Section 1 Name", "Section 2 Name"]

Return ONLY the JSON array."""


# =============================================================================
# INTENT PARSER
# =============================================================================

class IntentParser:
    """
    Parses SOW/requirements documents to extract structured requirements.
    
    Uses local LLMs first (Mistral), falls back to Claude for complex docs.
    """
    
    # Requirement categories
    CATEGORIES = [
        'functional',
        'technical', 
        'integration',
        'data',
        'reporting',
        'security',
        'other'
    ]
    
    def __init__(self, project_id: str = None):
        """
        Initialize the parser.
        
        Args:
            project_id: Project ID for tracking
        """
        self.project_id = project_id
        self.orchestrator = None
        
        if LLM_AVAILABLE:
            try:
                self.orchestrator = LLMOrchestrator()
                logger.info("[INTENT-PARSER] LLM orchestrator initialized")
            except Exception as e:
                logger.warning(f"[INTENT-PARSER] LLM orchestrator failed: {e}")
    
    def parse_document(self, text: str, filename: str = "document",
                       metadata: Dict = None) -> List[ParsedRequirement]:
        """
        Parse a document to extract requirements.
        
        Args:
            text: Document text content
            filename: Source filename
            metadata: Optional metadata (page numbers, sections)
            
        Returns:
            List of ParsedRequirement objects
        """
        if not text or len(text) < 50:
            logger.warning("[INTENT-PARSER] Document too short to parse")
            return []
        
        logger.info(f"[INTENT-PARSER] Parsing document: {filename} ({len(text)} chars)")
        
        requirements = []
        
        # For long documents, chunk and parse
        if len(text) > 8000:
            requirements = self._parse_chunked(text, filename, metadata)
        else:
            requirements = self._parse_full(text, filename, metadata)
        
        # Deduplicate
        requirements = self._deduplicate(requirements)
        
        # Generate IDs
        for i, req in enumerate(requirements):
            if not req.requirement_id:
                req.requirement_id = self._generate_id(req.text, filename, i)
        
        logger.info(f"[INTENT-PARSER] Extracted {len(requirements)} requirements from {filename}")
        
        return requirements
    
    def _parse_full(self, text: str, filename: str, 
                   metadata: Dict = None) -> List[ParsedRequirement]:
        """Parse a full document in one pass."""
        prompt = REQUIREMENTS_EXTRACTION_PROMPT.format(text=text)
        
        raw_reqs = self._call_llm(prompt)
        if not raw_reqs:
            return []
        
        return self._convert_to_requirements(raw_reqs, filename, metadata)
    
    def _parse_chunked(self, text: str, filename: str,
                      metadata: Dict = None) -> List[ParsedRequirement]:
        """Parse a long document in chunks."""
        requirements = []
        
        # Split into chunks of ~4000 chars with overlap
        chunk_size = 4000
        overlap = 500
        chunks = []
        
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        logger.info(f"[INTENT-PARSER] Processing {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            chunk_meta = {**(metadata or {}), 'chunk': i + 1}
            chunk_reqs = self._parse_full(chunk, filename, chunk_meta)
            requirements.extend(chunk_reqs)
        
        return requirements
    
    def _call_llm(self, prompt: str) -> Optional[List[Dict]]:
        """Call LLM to extract requirements."""
        if not self.orchestrator:
            logger.warning("[INTENT-PARSER] No LLM available - using pattern matching")
            return self._fallback_extraction(prompt)
        
        try:
            # Try Mistral first
            result, success = self.orchestrator._call_ollama(
                model="mistral:7b",
                prompt=prompt,
                system_prompt="You are a precise requirements extraction assistant. Extract all requirements from documents. Return only valid JSON.",
                project_id=self.project_id,
                processor="intent_parser"
            )
            
            if success and result:
                parsed = self._parse_json_array(result)
                if parsed:
                    return parsed
            
            # Fallback to Claude
            logger.info("[INTENT-PARSER] Trying Claude fallback")
            result = self._call_claude(prompt)
            if result:
                return self._parse_json_array(result)
                
        except Exception as e:
            logger.error(f"[INTENT-PARSER] LLM call failed: {e}")
        
        return None
    
    def _call_claude(self, prompt: str) -> Optional[str]:
        """Fallback to Claude for complex documents."""
        if not self.orchestrator or not self.orchestrator.claude_api_key:
            return None
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.orchestrator.claude_api_key)
            
            response = client.messages.create(
                model=self.orchestrator.claude_model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if response.content:
                return response.content[0].text
                
        except Exception as e:
            logger.warning(f"[INTENT-PARSER] Claude call failed: {e}")
        
        return None
    
    def _parse_json_array(self, response: str) -> Optional[List[Dict]]:
        """Parse JSON array from LLM response."""
        if not response:
            return None
        
        # Clean response
        response = response.strip()
        
        # Try direct parse
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON array
        try:
            match = re.search(r'\[[\s\S]*\]', response)
            if match:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
        except (json.JSONDecodeError, AttributeError):
            pass
        
        return None
    
    def _convert_to_requirements(self, raw_reqs: List[Dict], filename: str,
                                 metadata: Dict = None) -> List[ParsedRequirement]:
        """Convert raw LLM output to ParsedRequirement objects."""
        requirements = []
        
        for raw in raw_reqs:
            if not isinstance(raw, dict):
                continue
            
            text = raw.get('text', '')
            if not text or len(text) < 10:
                continue
            
            # Normalize category
            category = raw.get('category', 'other').lower()
            if category not in self.CATEGORIES:
                category = 'other'
            
            # Normalize priority
            priority = raw.get('priority', 'medium').lower()
            if priority not in ['high', 'medium', 'low']:
                priority = 'medium'
            
            req = ParsedRequirement(
                requirement_id='',  # Generated later
                text=text,
                category=category,
                priority=priority,
                source_file=filename,
                source_page=metadata.get('page') if metadata else None,
                source_section=raw.get('section'),
                deliverable=raw.get('deliverable'),
                acceptance_criteria=raw.get('acceptance_criteria', []),
                dependencies=raw.get('dependencies', []),
                stakeholder=raw.get('stakeholder'),
                deadline=raw.get('deadline'),
            )
            requirements.append(req)
        
        return requirements
    
    def _fallback_extraction(self, prompt: str) -> Optional[List[Dict]]:
        """Pattern-based extraction when LLM unavailable."""
        # Extract the document text from prompt
        match = re.search(r'DOCUMENT TEXT:\n(.*?)(?:\n\nExtract|$)', prompt, re.DOTALL)
        if not match:
            return None
        
        text = match.group(1)
        requirements = []
        
        # Look for requirement patterns
        patterns = [
            r'(?:shall|must|will|should|requires?)\s+(.{20,200}?)(?:\.|$)',
            r'(?:requirement|deliverable):\s*(.{20,200}?)(?:\.|$)',
            r'(?:•|▪|►|-|\d+\.)\s*(.{20,200}?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                requirements.append({
                    'text': m.strip(),
                    'category': 'other',
                    'priority': 'medium',
                })
        
        return requirements if requirements else None
    
    def _deduplicate(self, requirements: List[ParsedRequirement]) -> List[ParsedRequirement]:
        """Remove duplicate requirements."""
        seen = set()
        unique = []
        
        for req in requirements:
            # Normalize text for comparison
            normalized = re.sub(r'\s+', ' ', req.text.lower().strip())
            
            # Check similarity threshold (exact match for now)
            if normalized not in seen:
                seen.add(normalized)
                unique.append(req)
        
        return unique
    
    def _generate_id(self, text: str, filename: str, index: int) -> str:
        """Generate a unique requirement ID."""
        # Create hash from text + filename
        content = f"{filename}:{text[:100]}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"REQ-{hash_val.upper()}"
    
    def update_coverage(self, requirements: List[ParsedRequirement],
                       reality_data: List[Dict],
                       config_data: List[Dict]) -> List[ParsedRequirement]:
        """
        Update requirement coverage scores based on reality/config data.
        
        Args:
            requirements: List of requirements to check
            reality_data: Data from Reality gatherer
            config_data: Data from Configuration gatherer
            
        Returns:
            Requirements with updated coverage_score
        """
        # This would use LLM to assess if each requirement is covered
        # by the provided reality and configuration data
        # For now, return as-is (implementation TBD)
        return requirements


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_sow(text: str, filename: str = "sow.pdf", 
              project_id: str = None) -> List[ParsedRequirement]:
    """
    Convenience function to parse a SOW document.
    
    Args:
        text: Document text
        filename: Source filename
        project_id: Project ID
        
    Returns:
        List of ParsedRequirement objects
    """
    parser = IntentParser(project_id=project_id)
    return parser.parse_document(text, filename)


def requirements_to_dict(requirements: List[ParsedRequirement]) -> List[Dict]:
    """Convert requirements to list of dicts for JSON/storage."""
    return [r.to_dict() for r in requirements]
