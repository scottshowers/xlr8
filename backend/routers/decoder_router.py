"""
DOMAIN DECODER API - Consultant Knowledge Management
=====================================================

Endpoints for managing domain knowledge (tribal knowledge).

GET  /decoder              - List all knowledge entries
GET  /decoder/search       - Search knowledge
GET  /decoder/domain/{d}   - Get entries by domain
POST /decoder              - Add new knowledge
PUT  /decoder/{id}         - Update entry
DELETE /decoder/{id}       - Soft-delete entry

Author: XLR8 Team
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["domain-decoder"])


# =============================================================================
# MODELS
# =============================================================================

class DecoderEntryCreate(BaseModel):
    pattern: str
    meaning: str
    domain: str = 'general'
    category: str = 'general'
    example: Optional[str] = None
    confidence: float = 1.0
    source: Optional[str] = None


class DecoderEntryUpdate(BaseModel):
    pattern: Optional[str] = None
    meaning: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    example: Optional[str] = None
    confidence: Optional[float] = None
    is_active: Optional[bool] = None


class DecoderEntryResponse(BaseModel):
    id: str
    pattern: str
    meaning: str
    domain: str
    category: str
    example: Optional[str] = None
    confidence: float = 1.0
    added_by: Optional[str] = None
    source: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


# =============================================================================
# IMPORT DECODER SERVICE
# =============================================================================

try:
    from backend.utils.domain_decoder import (
        get_decoder, 
        DECODER_CATEGORIES, 
        DECODER_DOMAINS,
        seed_initial_knowledge
    )
except ImportError:
    from utils.domain_decoder import (
        get_decoder, 
        DECODER_CATEGORIES, 
        DECODER_DOMAINS,
        seed_initial_knowledge
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("")
async def list_all_knowledge():
    """
    Get all active domain knowledge entries.
    
    Returns all the "tribal knowledge" that makes XLR8 smart.
    """
    decoder = get_decoder()
    entries = decoder.get_all()
    
    return {
        "success": True,
        "count": len(entries),
        "entries": [e.to_dict() for e in entries],
        "domains": DECODER_DOMAINS,
        "categories": DECODER_CATEGORIES
    }


@router.get("/search")
async def search_knowledge(q: str = Query(..., description="Search query")):
    """
    Search knowledge entries by pattern, meaning, or example.
    """
    decoder = get_decoder()
    entries = decoder.search(q)
    
    return {
        "success": True,
        "query": q,
        "count": len(entries),
        "entries": [e.to_dict() for e in entries]
    }


@router.get("/decode")
async def decode_text(
    text: str = Query(..., description="Text to decode"),
    domain: Optional[str] = Query(None, description="Filter by domain")
):
    """
    Find all knowledge entries that match/explain the given text.
    
    This is how the intelligence engine uses domain knowledge -
    it passes in a column name, code, or question and gets back
    all relevant knowledge.
    """
    decoder = get_decoder()
    matches = decoder.decode(text, domain)
    
    return {
        "success": True,
        "text": text,
        "domain_filter": domain,
        "matches": len(matches),
        "knowledge": [e.to_dict() for e in matches]
    }


@router.get("/domain/{domain}")
async def get_by_domain(domain: str):
    """
    Get all knowledge entries for a specific domain.
    
    Domains: earnings, deductions, taxes, benefits, hr, time, gl, general
    """
    if domain not in DECODER_DOMAINS and domain != 'all':
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain. Valid domains: {list(DECODER_DOMAINS.keys())}"
        )
    
    decoder = get_decoder()
    
    if domain == 'all':
        entries = decoder.get_all()
    else:
        entries = decoder.get_by_domain(domain)
    
    return {
        "success": True,
        "domain": domain,
        "domain_description": DECODER_DOMAINS.get(domain, ''),
        "count": len(entries),
        "entries": [e.to_dict() for e in entries]
    }


@router.get("/category/{category}")
async def get_by_category(category: str):
    """
    Get all knowledge entries for a specific category.
    
    Categories: code_interpretation, file_relationship, business_rule, 
                signal_pattern, vendor_specific, compliance_flag
    """
    if category not in DECODER_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Valid categories: {list(DECODER_CATEGORIES.keys())}"
        )
    
    decoder = get_decoder()
    entries = decoder.get_by_category(category)
    
    return {
        "success": True,
        "category": category,
        "category_description": DECODER_CATEGORIES.get(category, ''),
        "count": len(entries),
        "entries": [e.to_dict() for e in entries]
    }


@router.post("")
async def add_knowledge(entry: DecoderEntryCreate):
    """
    Add new domain knowledge.
    
    This is how consultants contribute their expertise to make XLR8 smarter.
    """
    decoder = get_decoder()
    
    result = decoder.add(
        pattern=entry.pattern,
        meaning=entry.meaning,
        domain=entry.domain,
        category=entry.category,
        example=entry.example,
        confidence=entry.confidence,
        source=entry.source
    )
    
    if result:
        return {
            "success": True,
            "message": f"Knowledge added: {entry.pattern}",
            "entry": result.to_dict()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to add knowledge entry"
        )


@router.put("/{entry_id}")
async def update_knowledge(entry_id: str, updates: DecoderEntryUpdate):
    """
    Update an existing knowledge entry.
    """
    decoder = get_decoder()
    
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(
            status_code=400,
            detail="No updates provided"
        )
    
    success = decoder.update(entry_id, update_dict)
    
    if success:
        return {
            "success": True,
            "message": f"Knowledge entry {entry_id} updated"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to update knowledge entry"
        )


@router.delete("/{entry_id}")
async def delete_knowledge(entry_id: str):
    """
    Soft-delete a knowledge entry (sets is_active = False).
    """
    decoder = get_decoder()
    success = decoder.delete(entry_id)
    
    if success:
        return {
            "success": True,
            "message": f"Knowledge entry {entry_id} deactivated"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete knowledge entry"
        )


@router.post("/seed")
async def seed_knowledge():
    """
    Seed the database with initial domain knowledge.
    
    This adds the built-in knowledge (UKG patterns, common codes, etc.)
    that come with XLR8 out of the box.
    """
    try:
        count = seed_initial_knowledge()
        return {
            "success": True,
            "message": f"Seeded {count} knowledge entries",
            "count": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Seed failed: {str(e)}"
        )


@router.get("/meta")
async def get_metadata():
    """
    Get metadata about available domains and categories.
    
    Useful for building UI dropdowns.
    """
    return {
        "success": True,
        "domains": [
            {"key": k, "description": v} 
            for k, v in DECODER_DOMAINS.items()
        ],
        "categories": [
            {"key": k, "description": v}
            for k, v in DECODER_CATEGORIES.items()
        ]
    }
