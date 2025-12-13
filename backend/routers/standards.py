"""
Standards Upload Router for XLR8
================================

Copied directly from working upload.py pattern.
No guessing, just match what works.

Deploy to: backend/routers/standards.py
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from datetime import datetime
import sys
import os
import json
import traceback
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# IMPORTS - Same pattern as upload.py
# =============================================================================

try:
    from backend.utils.standards_processor import (
        process_pdf,
        process_text,
        get_rule_registry,
        search_standards
    )
    STANDARDS_PROCESSOR_AVAILABLE = True
except ImportError:
    try:
        from utils.standards_processor import (
            process_pdf,
            process_text,
            get_rule_registry,
            search_standards
        )
        STANDARDS_PROCESSOR_AVAILABLE = True
    except ImportError as e:
        STANDARDS_PROCESSOR_AVAILABLE = False
        logger.warning(f"Standards processor not available: {e}")

try:
    from backend.utils.compliance_engine import get_compliance_engine
    COMPLIANCE_ENGINE_AVAILABLE = True
except ImportError:
    try:
        from utils.compliance_engine import get_compliance_engine
        COMPLIANCE_ENGINE_AVAILABLE = True
    except ImportError as e:
        COMPLIANCE_ENGINE_AVAILABLE = False
        logger.warning(f"Compliance engine not available: {e}")

try:
    from backend.utils.structured_data_handler import StructuredDataHandler
    STRUCTURED_HANDLER_AVAILABLE = True
except ImportError:
    try:
        from utils.structured_data_handler import StructuredDataHandler
        STRUCTURED_HANDLER_AVAILABLE = True
    except ImportError:
        STRUCTURED_HANDLER_AVAILABLE = False


# =============================================================================
# DEBUG ENDPOINT - Same pattern as upload.py
# =============================================================================

@router.get("/standards/debug")
async def debug_features():
    """Debug endpoint to check what features are available"""
    return {
        "version": "2025-12-13-standards-v1",
        "standards_processor_available": STANDARDS_PROCESSOR_AVAILABLE,
        "compliance_engine_available": COMPLIANCE_ENGINE_AVAILABLE,
        "structured_handler_available": STRUCTURED_HANDLER_AVAILABLE,
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/standards/health")
async def health_check():
    """Check standards layer health."""
    status = {
        "standards_processor": STANDARDS_PROCESSOR_AVAILABLE,
        "compliance_engine": COMPLIANCE_ENGINE_AVAILABLE,
        "rules_loaded": 0,
        "documents_loaded": 0
    }
    
    if STANDARDS_PROCESSOR_AVAILABLE:
        try:
            registry = get_rule_registry()
            status["rules_loaded"] = len(registry.rules)
            status["documents_loaded"] = len(registry.documents)
        except:
            pass
    
    return status


# =============================================================================
# UPLOAD ENDPOINT - Matches upload.py exactly
# =============================================================================

@router.post("/standards/upload")
async def upload_standards_document(
    file: UploadFile = File(...),
    domain: str = Form(default="general"),
    title: Optional[str] = Form(default=None)
):
    """
    Upload a standards document for rule extraction.
    
    Matches the upload.py pattern exactly.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        filename = file.filename
        ext = filename.split('.')[-1].lower()
        
        # Check file extension
        allowed_extensions = ['pdf', 'docx', 'doc', 'txt', 'md']
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        logger.info(f"[STANDARDS] Upload received: {filename}, domain={domain}")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"[STANDARDS] File size: {file_size} bytes")
        
        # Check processor availability
        if not STANDARDS_PROCESSOR_AVAILABLE:
            raise HTTPException(status_code=503, detail="Standards processor not available")
        
        # Save to temp file
        file_path = f"/tmp/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"[STANDARDS] Saved to {file_path}")
        
        try:
            # Process based on file type
            if ext == 'pdf':
                doc = process_pdf(file_path, domain)
            else:
                # Read as text
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                doc = process_text(text, filename, domain)
            
            # Override title if provided
            if title:
                doc.title = title
            
            # Add to registry
            registry = get_rule_registry()
            registry.add_document(doc)
            
            logger.info(f"[STANDARDS] Extracted {len(doc.rules)} rules from {filename}")
            
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
            
        finally:
            # Cleanup temp file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[STANDARDS] Upload failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RULES ENDPOINTS
# =============================================================================

@router.get("/standards/rules")
async def list_rules(
    domain: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
):
    """List all extracted rules."""
    if not STANDARDS_PROCESSOR_AVAILABLE:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = get_rule_registry()
        
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


@router.get("/standards/rules/search")
async def search_rules_endpoint(
    query: str,
    domain: Optional[str] = None,
    limit: int = 10
):
    """Search for relevant rules."""
    if not STANDARDS_PROCESSOR_AVAILABLE:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        results = search_standards(query, domain)
        return {
            "query": query,
            "results": results[:limit]
        }
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


# =============================================================================
# DOCUMENTS ENDPOINTS
# =============================================================================

@router.get("/standards/documents")
async def list_documents():
    """List all processed standards documents."""
    if not STANDARDS_PROCESSOR_AVAILABLE:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        registry = get_rule_registry()
        return {
            "total": len(registry.documents),
            "documents": [doc.to_dict() for doc in registry.documents.values()]
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to list documents: {e}")


# =============================================================================
# COMPLIANCE ENDPOINTS
# =============================================================================

@router.post("/standards/compliance/check/{project_id}")
async def run_compliance_scan(
    project_id: str,
    domain: Optional[str] = None
):
    """Run compliance scan on a project."""
    if not COMPLIANCE_ENGINE_AVAILABLE:
        raise HTTPException(503, "Compliance engine not available")
    
    if not STANDARDS_PROCESSOR_AVAILABLE:
        raise HTTPException(503, "Standards processor not available")
    
    try:
        # Get database handler
        if not STRUCTURED_HANDLER_AVAILABLE:
            raise HTTPException(503, "Database handler not available")
        
        handler = StructuredDataHandler()
        handler.set_project(project_id)
        
        # Get rules
        registry = get_rule_registry()
        
        if domain:
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
        engine = get_compliance_engine()
        engine.set_db_handler(handler)
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
