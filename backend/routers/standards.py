"""
XLR8 STANDARDS ROUTER
=====================

API endpoints for the P4 Standards Layer:
- Upload and process standards documents
- Run compliance checks
- Retrieve findings

Deploy to: backend/routers/standards.py

Add to main.py:
    from routers import standards
    app.include_router(standards.router, prefix="/api", tags=["standards"])

Author: XLR8 Team
Version: 1.0.0 - P4 Standards Layer
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
import logging
import json
import os
import tempfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/standards", tags=["standards"])


# =============================================================================
# IMPORTS
# =============================================================================

def _get_standards_processor():
    """Get standards processor module."""
    try:
        from utils.standards_processor import (
            process_pdf, 
            process_text,
            get_rule_registry,
            search_standards
        )
        return {
            "process_pdf": process_pdf,
            "process_text": process_text,
            "get_rule_registry": get_rule_registry,
            "search_standards": search_standards
        }
    except ImportError as e:
        logger.error(f"[STANDARDS] Processor not available: {e}")
        return None


def _get_compliance_engine():
    """Get compliance engine."""
    try:
        from utils.compliance_engine import (
            get_compliance_engine,
            run_compliance_check,
            check_single_rule
        )
        return {
            "get_engine": get_compliance_engine,
            "run_check": run_compliance_check,
            "check_rule": check_single_rule
        }
    except ImportError as e:
        logger.error(f"[STANDARDS] Compliance engine not available: {e}")
        return None


def _get_db_handler(project_id: str):
    """Get database handler for a project."""
    try:
        from utils.structured_data_handler import StructuredDataHandler
        handler = StructuredDataHandler()
        handler.set_project(project_id)
        return handler
    except ImportError:
        try:
            from utils.duckdb_handler import DuckDBHandler
            return DuckDBHandler()
        except:
            return None


# =============================================================================
# UPLOAD & PROCESS STANDARDS
# =============================================================================

@router.post("/upload")
async def upload_standards_document(
    file: UploadFile = File(...),
    domain: str = Form(default="general"),
    title: str = Form(default=None)
):
    """
    Upload and process a standards document.
    
    Extracts compliance rules from the document and stores them
    in the rule registry for use in compliance checks.
    
    Args:
        file: PDF or text file containing standards
        domain: Category (e.g., "retirement", "tax", "benefits")
        title: Optional title override
    
    Returns:
        Document info with extracted rules count
    """
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    filename = file.filename or "standards.pdf"
    
    # Save to temp file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {e}")
    
    try:
        # Process based on file type
        if filename.lower().endswith('.pdf'):
            doc = processor["process_pdf"](tmp_path, domain)
        else:
            # Read as text
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            doc = processor["process_text"](text, filename, domain)
        
        # Override title if provided
        if title:
            doc.title = title
        
        # Add to registry
        registry = processor["get_rule_registry"]()
        registry.add_document(doc)
        
        return {
            "success": True,
            "document_id": doc.document_id,
            "filename": doc.filename,
            "title": doc.title,
            "domain": doc.domain,
            "rules_extracted": len(doc.rules),
            "page_count": doc.page_count,
            "rules": [r.to_dict() for r in doc.rules[:10]]  # Preview first 10
        }
        
    except Exception as e:
        logger.error(f"[STANDARDS] Processing failed: {e}")
        raise HTTPException(500, f"Failed to process document: {e}")
        
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass


@router.post("/upload/text")
async def upload_standards_text(
    text: str,
    document_name: str,
    domain: str = "general"
):
    """
    Process standards from raw text.
    
    Useful for pasting in requirements or rules directly.
    """
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        doc = processor["process_text"](text, document_name, domain)
        
        registry = processor["get_rule_registry"]()
        registry.add_document(doc)
        
        return {
            "success": True,
            "document_id": doc.document_id,
            "title": doc.title,
            "rules_extracted": len(doc.rules),
            "rules": [r.to_dict() for r in doc.rules]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to process text: {e}")


# =============================================================================
# RULE MANAGEMENT
# =============================================================================

@router.get("/rules")
async def list_rules(
    domain: str = None,
    category: str = None,
    limit: int = 100
):
    """
    List all extracted rules.
    
    Args:
        domain: Filter by domain
        category: Filter by category
        limit: Max rules to return
    """
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = processor["get_rule_registry"]()
        
        if domain:
            rules = registry.get_rules_by_domain(domain)
        else:
            rules = registry.get_all_rules()
        
        # Filter by category if specified
        if category:
            rules = [r for r in rules if r.category == category]
        
        return {
            "total": len(rules),
            "rules": [r.to_dict() for r in rules[:limit]]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to list rules: {e}")


@router.get("/rules/search")
async def search_rules(
    query: str,
    domain: str = None,
    limit: int = 10
):
    """
    Search for relevant rules using semantic search.
    
    Args:
        query: Search query (e.g., "catch-up contributions age 50")
        domain: Filter by domain
        limit: Max results
    """
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        results = processor["search_standards"](query, domain)
        return {
            "query": query,
            "results": results[:limit]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get a specific rule by ID."""
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = processor["get_rule_registry"]()
        
        if rule_id in registry.rules:
            return registry.rules[rule_id].to_dict()
        
        raise HTTPException(404, f"Rule not found: {rule_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get rule: {e}")


# =============================================================================
# COMPLIANCE CHECKING
# =============================================================================

@router.post("/compliance/check/{project_id}")
async def run_compliance_scan(
    project_id: str,
    domain: str = None,
    rule_ids: List[str] = None
):
    """
    Run compliance scan on a project.
    
    Checks all applicable rules against the project's data
    and returns findings for any non-compliant items.
    
    Args:
        project_id: Project to scan
        domain: Filter rules by domain
        rule_ids: Specific rule IDs to check (optional)
    
    Returns:
        List of compliance findings
    """
    compliance = _get_compliance_engine()
    if not compliance:
        raise HTTPException(503, "Compliance engine not available")
    
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    # Get database handler
    db_handler = _get_db_handler(project_id)
    if not db_handler:
        raise HTTPException(503, "Database handler not available")
    
    try:
        engine = compliance["get_engine"]()
        engine.set_db_handler(db_handler)
        
        # Get rules
        registry = processor["get_rule_registry"]()
        
        if rule_ids:
            rules = [registry.rules[rid].to_dict() 
                    for rid in rule_ids 
                    if rid in registry.rules]
        elif domain:
            rules = [r.to_dict() for r in registry.get_rules_by_domain(domain)]
        else:
            rules = [r.to_dict() for r in registry.get_all_rules()]
        
        if not rules:
            return {
                "project_id": project_id,
                "rules_checked": 0,
                "findings": [],
                "message": "No rules found to check. Upload standards documents first."
            }
        
        # Run scan
        findings = engine.run_compliance_scan(project_id, rules=rules)
        
        return {
            "project_id": project_id,
            "rules_checked": len(rules),
            "findings_count": len(findings),
            "findings": [f.to_dict() for f in findings],
            "compliant_count": len(rules) - len(findings)
        }
        
    except Exception as e:
        logger.error(f"[STANDARDS] Compliance scan failed: {e}")
        raise HTTPException(500, f"Compliance scan failed: {e}")


@router.post("/compliance/check-rule/{project_id}")
async def check_single_rule_endpoint(
    project_id: str,
    rule: dict
):
    """
    Check a single rule against project data.
    
    Useful for testing rules or ad-hoc checks.
    
    Args:
        project_id: Project to check
        rule: Rule definition to check
    
    Returns:
        Finding if non-compliant, null if compliant
    """
    compliance = _get_compliance_engine()
    if not compliance:
        raise HTTPException(503, "Compliance engine not available")
    
    db_handler = _get_db_handler(project_id)
    if not db_handler:
        raise HTTPException(503, "Database handler not available")
    
    try:
        finding = compliance["check_rule"](rule, project_id, db_handler)
        
        return {
            "project_id": project_id,
            "rule_id": rule.get("rule_id", "ad-hoc"),
            "compliant": finding is None,
            "finding": finding
        }
        
    except Exception as e:
        raise HTTPException(500, f"Check failed: {e}")


# =============================================================================
# DOCUMENTS
# =============================================================================

@router.get("/documents")
async def list_documents():
    """List all processed standards documents."""
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = processor["get_rule_registry"]()
        
        return {
            "total": len(registry.documents),
            "documents": [doc.to_dict() for doc in registry.documents.values()]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to list documents: {e}")


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get a specific standards document."""
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = processor["get_rule_registry"]()
        
        if document_id in registry.documents:
            return registry.documents[document_id].to_dict()
        
        raise HTTPException(404, f"Document not found: {document_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get document: {e}")


# =============================================================================
# EXPORT
# =============================================================================

@router.get("/export")
async def export_all():
    """Export all standards and rules as JSON."""
    processor = _get_standards_processor()
    if not processor:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = processor["get_rule_registry"]()
        return registry.export_rules()
        
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")


# =============================================================================
# HEALTH
# =============================================================================

@router.get("/health")
async def health_check():
    """Check standards layer health."""
    processor = _get_standards_processor()
    compliance = _get_compliance_engine()
    
    status = {
        "standards_processor": processor is not None,
        "compliance_engine": compliance is not None,
        "rules_loaded": 0,
        "documents_loaded": 0
    }
    
    if processor:
        try:
            registry = processor["get_rule_registry"]()
            status["rules_loaded"] = len(registry.rules)
            status["documents_loaded"] = len(registry.documents)
        except:
            pass
    
    return status
