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

PERSISTENCE: Rules stored in Supabase (survive Railway redeploys)

LLM STRATEGY:
- PRIMARY: Groq (Llama 3.3 70B) - fast, free, capable
- FALLBACK: Claude - only if Groq fails

Deploy to: backend/utils/standards_processor.py

Author: XLR8 Team
Version: 1.2.0 - Groq first, Claude fallback only (NO MONEY GRAB)
"""

import os
import re
import json
import logging
import requests
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
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExtractedRule':
        """Create ExtractedRule from dictionary."""
        return cls(
            rule_id=data.get("rule_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            applies_to=data.get("applies_to", {}),
            requirement=data.get("requirement", {}),
            source_document=data.get("source_document", ""),
            source_page=data.get("source_page"),
            source_section=data.get("source_section"),
            source_text=data.get("source_text", ""),
            category=data.get("category", "general"),
            severity=data.get("severity", "medium"),
            effective_date=data.get("effective_date"),
            check_type=data.get("check_type", "data"),
            suggested_sql_pattern=data.get("suggested_sql_pattern")
        )


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
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StandardsDocument':
        """Create StandardsDocument from dictionary."""
        doc = cls(
            document_id=data.get("document_id", ""),
            filename=data.get("filename", ""),
            title=data.get("title", ""),
            domain=data.get("domain", "general"),
            processed_at=data.get("processed_at", datetime.now().isoformat()),
            page_count=data.get("page_count", 0),
            raw_text=data.get("raw_text", "")
        )
        # Convert rules if present
        rules_data = data.get("rules", [])
        doc.rules = [ExtractedRule.from_dict(r) if isinstance(r, dict) else r for r in rules_data]
        return doc


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

_supabase_client = None

def _get_supabase():
    """Get Supabase client (singleton)."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            
            if url and key:
                _supabase_client = create_client(url, key)
                logger.info("[STANDARDS] Supabase client initialized")
            else:
                logger.warning("[STANDARDS] Supabase credentials not found")
        except ImportError:
            logger.warning("[STANDARDS] Supabase library not available")
        except Exception as e:
            logger.error(f"[STANDARDS] Supabase init failed: {e}")
    return _supabase_client


# =============================================================================
# LLM INTEGRATION - GROQ FIRST, CLAUDE FALLBACK ONLY
# =============================================================================

def _call_groq(prompt: str, system_prompt: str = None) -> tuple:
    """
    Call Groq API (Llama 3.3 70B) for rule extraction.
    
    Returns: (response_text, success)
    """
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    
    if not groq_api_key:
        logger.warning("[STANDARDS] No GROQ_API_KEY - cannot use Groq")
        return "", False
    
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 8192
            },
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"[STANDARDS] Groq response: {len(content)} chars")
            return content, True
        elif response.status_code == 429:
            logger.warning("[STANDARDS] Groq rate limited")
            return "", False
        else:
            logger.warning(f"[STANDARDS] Groq error: {response.status_code} - {response.text[:200]}")
            return "", False
            
    except requests.exceptions.Timeout:
        logger.warning("[STANDARDS] Groq timeout")
        return "", False
    except Exception as e:
        logger.error(f"[STANDARDS] Groq call failed: {e}")
        return "", False


def _call_claude_fallback(prompt: str, system_prompt: str = None) -> tuple:
    """
    Call Claude API as FALLBACK ONLY when Groq fails.
    
    Returns: (response_text, success)
    """
    claude_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    if not claude_api_key:
        logger.warning("[STANDARDS] No ANTHROPIC_API_KEY - cannot use Claude fallback")
        return "", False
    
    try:
        headers = {
            "x-api-key": claude_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",  # Use cheapest model for fallback
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("content", [{}])[0].get("text", "")
            
            # Track cost (for visibility)
            try:
                from utils.cost_tracker import track_cost
                input_tokens = result.get("usage", {}).get("input_tokens", 0)
                output_tokens = result.get("usage", {}).get("output_tokens", 0)
                track_cost("claude_haiku", "standards_extraction_fallback", input_tokens, output_tokens)
            except:
                pass
            
            logger.warning(f"[STANDARDS] Claude FALLBACK used: {len(content)} chars")
            return content, True
        else:
            logger.error(f"[STANDARDS] Claude error: {response.status_code}")
            return "", False
            
    except Exception as e:
        logger.error(f"[STANDARDS] Claude fallback failed: {e}")
        return "", False


def _call_llm(prompt: str, system_prompt: str = None) -> str:
    """
    Call LLM for rule extraction.
    
    STRATEGY:
    1. Groq (Llama 3.3 70B) - PRIMARY, fast, free
    2. Claude (Haiku) - FALLBACK ONLY if Groq fails
    
    This is NOT a money grab. Groq handles this fine.
    """
    
    # Try Groq first (PRIMARY)
    result, success = _call_groq(prompt, system_prompt)
    if success and result:
        logger.info("[STANDARDS] Using Groq (Llama 3.3 70B)")
        return result
    
    # Fallback to Claude ONLY if Groq failed
    logger.warning("[STANDARDS] Groq failed, falling back to Claude...")
    result, success = _call_claude_fallback(prompt, system_prompt)
    if success and result:
        return result
    
    logger.error("[STANDARDS] All LLM calls failed")
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
# RULE STORAGE & RETRIEVAL - WITH SUPABASE PERSISTENCE
# =============================================================================

class RuleRegistry:
    """
    Store and retrieve extracted rules.
    
    Persistence: Supabase (survives Railway redeploys)
    Search: ChromaDB for semantic search (rebuilt on startup)
    """
    
    # Supabase table names
    DOCUMENTS_TABLE = "standards_documents"
    RULES_TABLE = "standards_rules"
    
    def __init__(self):
        self.rules: Dict[str, ExtractedRule] = {}
        self.documents: Dict[str, StandardsDocument] = {}
        self.chroma_collection = None
        self._supabase_available = False
        
        # Initialize
        self._init_supabase()
        self._init_chroma()
        self._load_from_supabase()
    
    def _init_supabase(self):
        """Check if Supabase is available."""
        client = _get_supabase()
        if client:
            self._supabase_available = True
            logger.info("[STANDARDS] Supabase persistence enabled")
        else:
            logger.warning("[STANDARDS] Supabase not available - rules will not persist")
    
    def _init_chroma(self):
        """Initialize ChromaDB for rule search."""
        try:
            import chromadb
            client = chromadb.Client()
            self.chroma_collection = client.get_or_create_collection(
                name="xlr8_standards_rules",
                metadata={"description": "Extracted compliance rules"}
            )
            logger.info("[STANDARDS] ChromaDB initialized for rule search")
        except Exception as e:
            logger.warning(f"[STANDARDS] ChromaDB not available: {e}")
    
    def _load_from_supabase(self):
        """Load existing rules from Supabase on startup."""
        if not self._supabase_available:
            return
        
        client = _get_supabase()
        if not client:
            return
        
        try:
            # Load documents
            doc_result = client.table(self.DOCUMENTS_TABLE).select("*").execute()
            docs_loaded = 0
            
            for row in doc_result.data or []:
                try:
                    doc = StandardsDocument(
                        document_id=row["document_id"],
                        filename=row.get("filename", ""),
                        title=row.get("title", ""),
                        domain=row.get("domain", "general"),
                        processed_at=row.get("processed_at", ""),
                        page_count=row.get("page_count", 0),
                        raw_text=""  # Don't load raw text to save memory
                    )
                    self.documents[doc.document_id] = doc
                    docs_loaded += 1
                except Exception as e:
                    logger.warning(f"[STANDARDS] Failed to load document: {e}")
            
            # Load rules
            rules_result = client.table(self.RULES_TABLE).select("*").execute()
            rules_loaded = 0
            
            for row in rules_result.data or []:
                try:
                    rule = ExtractedRule(
                        rule_id=row["rule_id"],
                        title=row.get("title", ""),
                        description=row.get("description", ""),
                        applies_to=row.get("applies_to", {}),
                        requirement=row.get("requirement", {}),
                        source_document=row.get("source_document", ""),
                        source_page=row.get("source_page"),
                        source_section=row.get("source_section"),
                        source_text=row.get("source_text", ""),
                        category=row.get("category", "general"),
                        severity=row.get("severity", "medium"),
                        effective_date=row.get("effective_date"),
                        check_type=row.get("check_type", "data"),
                        suggested_sql_pattern=row.get("suggested_sql_pattern")
                    )
                    self.rules[rule.rule_id] = rule
                    
                    # Add to document's rules list
                    doc_id = row.get("document_id")
                    if doc_id and doc_id in self.documents:
                        self.documents[doc_id].rules.append(rule)
                    
                    # Add to ChromaDB for search
                    self._add_to_chroma(rule, row.get("domain", "general"))
                    
                    rules_loaded += 1
                except Exception as e:
                    logger.warning(f"[STANDARDS] Failed to load rule: {e}")
            
            logger.info(f"[STANDARDS] Loaded {docs_loaded} documents and {rules_loaded} rules from Supabase")
            
        except Exception as e:
            logger.error(f"[STANDARDS] Failed to load from Supabase: {e}")
    
    def _add_to_chroma(self, rule: ExtractedRule, domain: str):
        """Add a rule to ChromaDB for semantic search."""
        if not self.chroma_collection:
            return
        
        try:
            # Check if already exists
            try:
                self.chroma_collection.get(ids=[rule.rule_id])
                # Already exists, skip
                return
            except:
                pass
            
            self.chroma_collection.add(
                ids=[rule.rule_id],
                documents=[f"{rule.title}\n{rule.description}\n{rule.source_text}"],
                metadatas=[{
                    "category": rule.category,
                    "severity": rule.severity,
                    "domain": domain
                }]
            )
        except Exception as e:
            # Ignore duplicates
            if "already exists" not in str(e).lower():
                logger.warning(f"[STANDARDS] Failed to add rule to ChromaDB: {e}")
    
    def _save_document_to_supabase(self, doc: StandardsDocument):
        """Save a document to Supabase."""
        if not self._supabase_available:
            return
        
        client = _get_supabase()
        if not client:
            return
        
        try:
            data = {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "title": doc.title,
                "domain": doc.domain,
                "processed_at": doc.processed_at,
                "page_count": doc.page_count,
                "rule_count": len(doc.rules)
            }
            
            # Upsert (insert or update)
            client.table(self.DOCUMENTS_TABLE).upsert(data).execute()
            logger.info(f"[STANDARDS] Saved document {doc.document_id} to Supabase")
            
        except Exception as e:
            logger.error(f"[STANDARDS] Failed to save document to Supabase: {e}")
    
    def _save_rule_to_supabase(self, rule: ExtractedRule, doc: StandardsDocument):
        """Save a rule to Supabase."""
        if not self._supabase_available:
            return
        
        client = _get_supabase()
        if not client:
            return
        
        try:
            data = {
                "rule_id": rule.rule_id,
                "document_id": doc.document_id,
                "title": rule.title,
                "description": rule.description,
                "applies_to": rule.applies_to,
                "requirement": rule.requirement,
                "source_document": rule.source_document,
                "source_page": rule.source_page,
                "source_section": rule.source_section,
                "source_text": rule.source_text,
                "category": rule.category,
                "severity": rule.severity,
                "effective_date": rule.effective_date,
                "check_type": rule.check_type,
                "suggested_sql_pattern": rule.suggested_sql_pattern,
                "domain": doc.domain
            }
            
            # Upsert (insert or update)
            client.table(self.RULES_TABLE).upsert(data).execute()
            
        except Exception as e:
            logger.error(f"[STANDARDS] Failed to save rule to Supabase: {e}")
    
    def add_document(self, doc: StandardsDocument):
        """Add a processed document and its rules to the registry."""
        # Add to memory
        self.documents[doc.document_id] = doc
        
        # Save document to Supabase
        self._save_document_to_supabase(doc)
        
        for rule in doc.rules:
            # Add to memory
            self.rules[rule.rule_id] = rule
            
            # Save rule to Supabase
            self._save_rule_to_supabase(rule, doc)
            
            # Add to ChromaDB for semantic search
            self._add_to_chroma(rule, doc.domain)
        
        logger.info(f"[STANDARDS] Added document {doc.document_id} with {len(doc.rules)} rules")
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its rules."""
        if document_id not in self.documents:
            return False
        
        doc = self.documents[document_id]
        
        # Delete rules from memory and ChromaDB
        for rule in doc.rules:
            if rule.rule_id in self.rules:
                del self.rules[rule.rule_id]
            
            if self.chroma_collection:
                try:
                    self.chroma_collection.delete(ids=[rule.rule_id])
                except:
                    pass
        
        # Delete from memory
        del self.documents[document_id]
        
        # Delete from Supabase
        if self._supabase_available:
            client = _get_supabase()
            if client:
                try:
                    client.table(self.RULES_TABLE).delete().eq("document_id", document_id).execute()
                    client.table(self.DOCUMENTS_TABLE).delete().eq("document_id", document_id).execute()
                    logger.info(f"[STANDARDS] Deleted document {document_id} from Supabase")
                except Exception as e:
                    logger.error(f"[STANDARDS] Failed to delete from Supabase: {e}")
        
        return True
    
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
        result = []
        for rule in self.rules.values():
            # Find the document for this rule
            for doc in self.documents.values():
                if doc.domain == domain and rule in doc.rules:
                    result.append(rule)
                    break
        return result
    
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
