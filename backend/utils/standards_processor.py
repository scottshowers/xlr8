"""
XLR8 STANDARDS PROCESSOR
========================

Extracts structured, executable rules from standards documents.
Domain-agnostic - works with any compliance doc, checklist, or guideline.

NO HARDCODING. The LLM reads the document and extracts:
- Requirements (what must be true)
- Thresholds (numeric limits)
- Conditions (who/what this applies to)
- Actions (what to do about it)

Deploy to: backend/utils/standards_processor.py

Author: XLR8 Team
Version: 1.0.0 - P4 Standards Layer
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ExtractedRule:
    """A single rule extracted from a standards document."""
    rule_id: str
    title: str
    description: str
    
    # The actual rule logic
    applies_to: Dict[str, Any]  # Conditions for when this rule applies
    requirement: Dict[str, Any]  # What must be true
    
    # Source tracking
    source_document: str
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    source_text: str = ""  # Original text for citation
    
    # Metadata
    category: str = "general"
    severity: str = "medium"  # low, medium, high, critical
    effective_date: Optional[str] = None
    
    # For execution
    check_type: str = "data"  # data, process, document
    suggested_sql_pattern: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "applies_to": self.applies_to,
            "requirement": self.requirement,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "source_section": self.source_section,
            "source_text": self.source_text,
            "category": self.category,
            "severity": self.severity,
            "effective_date": self.effective_date,
            "check_type": self.check_type,
            "suggested_sql_pattern": self.suggested_sql_pattern
        }


@dataclass
class StandardsDocument:
    """A processed standards document with extracted rules."""
    document_id: str
    filename: str
    title: str
    domain: str  # retirement, tax, benefits, hr, etc.
    rules: List[ExtractedRule] = field(default_factory=list)
    
    # Metadata
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    page_count: int = 0
    raw_text: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "title": self.title,
            "domain": self.domain,
            "rules": [r.to_dict() for r in self.rules],
            "processed_at": self.processed_at,
            "page_count": self.page_count,
            "rule_count": len(self.rules)
        }


# =============================================================================
# LLM INTEGRATION - Uses LLMOrchestrator like intelligence_engine
# =============================================================================

_orchestrator = None

def _get_orchestrator():
    """Get or create LLMOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            _orchestrator = LLMOrchestrator()
            logger.info("[STANDARDS] LLMOrchestrator initialized")
        except Exception as e:
            logger.error(f"[STANDARDS] Could not load LLMOrchestrator: {e}")
            return None
    return _orchestrator


def _call_llm(prompt: str, system_prompt: str = None) -> str:
    """Call LLM for rule extraction using LLMOrchestrator."""
    orchestrator = _get_orchestrator()
    
    if not orchestrator:
        logger.error("[STANDARDS] No LLM available for rule extraction")
        return ""
    
    try:
        # Use process_query which handles local vs Claude routing
        # We'll format as a simple query
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        # Try Claude directly since this is text extraction (not SQL)
        result, success = orchestrator._call_claude(
            prompt=prompt,
            system_prompt=system_prompt or "You are a compliance analyst extracting rules from documents.",
            operation="standards_extraction"
        )
        
        if success:
            logger.info(f"[STANDARDS] LLM response: {len(result)} chars")
            return result
        else:
            logger.error(f"[STANDARDS] LLM call failed: {result}")
            return ""
    
    except Exception as e:
        logger.error(f"[STANDARDS] LLM call failed: {e}")
        return ""


# =============================================================================
# RULE EXTRACTION
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are an expert compliance analyst. Your job is to extract specific, actionable rules from standards documents.

For each rule you identify, extract:
1. WHO it applies to (conditions/criteria)
2. WHAT must be true (the requirement)
3. WHAT to check (data fields, thresholds, conditions)
4. HOW serious it is (severity)

Focus on rules that can be verified against data:
- Numeric thresholds (age >= X, salary > Y)
- Required fields (must have X assigned)
- Valid values (code must be one of A, B, C)
- Relationships (if X then must have Y)

Output ONLY valid JSON. No explanations outside the JSON."""


EXTRACTION_PROMPT_TEMPLATE = """Analyze this standards document and extract all compliance rules.

DOCUMENT: {document_name}
SECTION: {section}

TEXT:
{text}

---

Extract rules as a JSON array. Each rule should have:
{{
  "title": "Brief title",
  "description": "Full description of the requirement",
  "applies_to": {{
    "description": "Who/what this applies to",
    "conditions": [
      {{"field": "field_name", "operator": ">=|<=|=|>|<|in|not_in", "value": "value"}}
    ]
  }},
  "requirement": {{
    "description": "What must be true",
    "checks": [
      {{"field": "field_name", "operator": "must_have|must_be|must_not_be", "value": "value or list"}}
    ]
  }},
  "category": "category like retirement, tax, benefits, compliance",
  "severity": "low|medium|high|critical",
  "source_text": "The exact quote from the document that defines this rule"
}}

Return ONLY the JSON array of rules. If no rules found, return empty array []."""


def extract_rules_from_text(
    text: str, 
    document_name: str,
    section: str = "Main",
    page: int = None
) -> List[ExtractedRule]:
    """Extract rules from a block of text using LLM."""
    
    if not text or len(text.strip()) < 50:
        return []
    
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        document_name=document_name,
        section=section,
        text=text[:8000]  # Limit text size
    )
    
    response = _call_llm(prompt, EXTRACTION_SYSTEM_PROMPT)
    
    if not response:
        return []
    
    # Parse JSON from response
    try:
        # Try to find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            rules_data = json.loads(json_match.group())
        else:
            logger.warning(f"[STANDARDS] No JSON array found in LLM response")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"[STANDARDS] Failed to parse LLM response as JSON: {e}")
        return []
    
    # Convert to ExtractedRule objects
    rules = []
    for i, rule_data in enumerate(rules_data):
        try:
            rule = ExtractedRule(
                rule_id=f"{document_name[:20]}_{section[:10]}_{i+1}".replace(" ", "_"),
                title=rule_data.get("title", "Untitled Rule"),
                description=rule_data.get("description", ""),
                applies_to=rule_data.get("applies_to", {}),
                requirement=rule_data.get("requirement", {}),
                source_document=document_name,
                source_page=page,
                source_section=section,
                source_text=rule_data.get("source_text", ""),
                category=rule_data.get("category", "general"),
                severity=rule_data.get("severity", "medium"),
                check_type="data"
            )
            rules.append(rule)
        except Exception as e:
            logger.warning(f"[STANDARDS] Failed to create rule from data: {e}")
    
    logger.info(f"[STANDARDS] Extracted {len(rules)} rules from {section}")
    return rules


# =============================================================================
# DOCUMENT PROCESSING
# =============================================================================

def process_pdf(file_path: str, domain: str = "general") -> StandardsDocument:
    """Process a PDF and extract all rules."""
    import hashlib
    
    filename = os.path.basename(file_path)
    doc_id = hashlib.md5(f"{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    
    logger.info(f"[STANDARDS] Processing PDF: {filename}")
    
    # Extract text from PDF
    full_text = ""
    page_count = 0
    
    try:
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                full_text += f"\n--- PAGE {i+1} ---\n{page_text}"
    except ImportError:
        logger.warning("[STANDARDS] pdfplumber not available, trying pypdf")
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                full_text += f"\n--- PAGE {i+1} ---\n{page_text}"
        except Exception as e:
            logger.error(f"[STANDARDS] Failed to extract PDF text: {e}")
            return StandardsDocument(
                document_id=doc_id,
                filename=filename,
                title=filename,
                domain=domain
            )
    
    # Extract title from first page
    title = filename
    first_lines = full_text[:500].split('\n')
    for line in first_lines:
        line = line.strip()
        if len(line) > 10 and len(line) < 200 and not line.startswith('---'):
            title = line
            break
    
    # Create document
    doc = StandardsDocument(
        document_id=doc_id,
        filename=filename,
        title=title,
        domain=domain,
        page_count=page_count,
        raw_text=full_text[:50000]  # Store limited raw text
    )
    
    # Extract rules from the document
    # Process in chunks to handle large documents
    chunk_size = 4000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    all_rules = []
    for i, chunk in enumerate(chunks):
        section = f"Section {i+1}"
        rules = extract_rules_from_text(chunk, filename, section)
        all_rules.extend(rules)
    
    doc.rules = all_rules
    logger.info(f"[STANDARDS] Processed {filename}: {len(all_rules)} rules extracted")
    
    return doc


def process_text(text: str, document_name: str, domain: str = "general") -> StandardsDocument:
    """Process raw text and extract rules."""
    import hashlib
    
    doc_id = hashlib.md5(f"{document_name}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    
    doc = StandardsDocument(
        document_id=doc_id,
        filename=document_name,
        title=document_name,
        domain=domain,
        raw_text=text[:50000]
    )
    
    rules = extract_rules_from_text(text, document_name, "Main")
    doc.rules = rules
    
    return doc


# =============================================================================
# RULE STORAGE & RETRIEVAL
# =============================================================================

class RuleRegistry:
    """
    Store and retrieve extracted rules.
    Uses ChromaDB for semantic search of rules.
    """
    
    def __init__(self):
        self.rules: Dict[str, ExtractedRule] = {}
        self.documents: Dict[str, StandardsDocument] = {}
        self.chroma_collection = None
        self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB for rule storage."""
        try:
            import chromadb
            client = chromadb.Client()
            self.chroma_collection = client.get_or_create_collection(
                name="xlr8_standards_rules",
                metadata={"description": "Extracted compliance rules"}
            )
            logger.info("[STANDARDS] ChromaDB initialized for rule storage")
        except Exception as e:
            logger.warning(f"[STANDARDS] ChromaDB not available: {e}")
    
    def add_document(self, doc: StandardsDocument):
        """Add a processed document and its rules to the registry."""
        self.documents[doc.document_id] = doc
        
        for rule in doc.rules:
            self.rules[rule.rule_id] = rule
            
            # Add to ChromaDB for semantic search
            if self.chroma_collection:
                try:
                    self.chroma_collection.add(
                        ids=[rule.rule_id],
                        documents=[f"{rule.title}\n{rule.description}\n{rule.source_text}"],
                        metadatas=[{
                            "document_id": doc.document_id,
                            "category": rule.category,
                            "severity": rule.severity,
                            "domain": doc.domain
                        }]
                    )
                except Exception as e:
                    logger.warning(f"[STANDARDS] Failed to add rule to ChromaDB: {e}")
        
        logger.info(f"[STANDARDS] Added document {doc.document_id} with {len(doc.rules)} rules")
    
    def search_rules(
        self, 
        query: str, 
        domain: str = None,
        category: str = None,
        limit: int = 10
    ) -> List[ExtractedRule]:
        """Search for relevant rules using semantic search."""
        
        if not self.chroma_collection:
            # Fallback to simple text matching
            results = []
            query_lower = query.lower()
            for rule in self.rules.values():
                if query_lower in rule.title.lower() or query_lower in rule.description.lower():
                    results.append(rule)
            return results[:limit]
        
        try:
            where_filter = {}
            if domain:
                where_filter["domain"] = domain
            if category:
                where_filter["category"] = category
            
            results = self.chroma_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter if where_filter else None
            )
            
            rule_ids = results.get("ids", [[]])[0]
            return [self.rules[rid] for rid in rule_ids if rid in self.rules]
            
        except Exception as e:
            logger.error(f"[STANDARDS] Search failed: {e}")
            return []
    
    def get_rules_by_domain(self, domain: str) -> List[ExtractedRule]:
        """Get all rules for a specific domain."""
        return [r for r in self.rules.values() 
                if self.documents.get(r.source_document, StandardsDocument("","","","")).domain == domain]
    
    def get_all_rules(self) -> List[ExtractedRule]:
        """Get all rules in the registry."""
        return list(self.rules.values())
    
    def export_rules(self) -> Dict:
        """Export all rules as JSON."""
        return {
            "documents": {did: doc.to_dict() for did, doc in self.documents.items()},
            "rule_count": len(self.rules),
            "exported_at": datetime.now().isoformat()
        }


# =============================================================================
# SINGLETON
# =============================================================================

_rule_registry: Optional[RuleRegistry] = None

def get_rule_registry() -> RuleRegistry:
    """Get the singleton rule registry."""
    global _rule_registry
    if _rule_registry is None:
        _rule_registry = RuleRegistry()
    return _rule_registry


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def process_and_register_pdf(file_path: str, domain: str = "general") -> StandardsDocument:
    """Process a PDF and register its rules."""
    doc = process_pdf(file_path, domain)
    registry = get_rule_registry()
    registry.add_document(doc)
    return doc


def search_standards(query: str, domain: str = None) -> List[Dict]:
    """Search for relevant standards rules."""
    registry = get_rule_registry()
    rules = registry.search_rules(query, domain=domain)
    return [r.to_dict() for r in rules]
