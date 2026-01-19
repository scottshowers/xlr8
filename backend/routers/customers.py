"""
Customers Router - Complete CRUD
Customers are the top-level entity. Each customer can have multiple engagements/playbooks.

IMPORTANT: customer.id (UUID) is the ONLY identifier used throughout the system.
- DuckDB tables: {customer_id}_{filename}_{sheet}
- All API calls: /customers/{customer_id}/...

Updated: January 2026 - Refactored from projects to customers
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProjectModel

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class CustomerCreate(BaseModel):
    """Schema for creating a customer"""
    name: str  # Customer name (e.g., "TEAM Inc")
    product: Optional[str] = None  # Primary product (UKG Pro, Workday, etc.)
    engagement_types: Optional[List[str]] = ["Implementation"]  # Can have multiple
    start_date: Optional[str] = None
    notes: Optional[str] = None
    playbooks: Optional[List[str]] = []  # Array of playbook IDs
    # Scope fields
    systems: Optional[List[str]] = []  # Array of system codes
    domains: Optional[List[str]] = []  # Array of domain codes
    functional_areas: Optional[List[dict]] = []  # Array of {domain, area} objects
    # Additional fields
    target_go_live: Optional[str] = None
    lead_name: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Schema for updating a customer"""
    name: Optional[str] = None
    product: Optional[str] = None
    engagement_types: Optional[List[str]] = None
    start_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    playbooks: Optional[List[str]] = None
    systems: Optional[List[str]] = None
    domains: Optional[List[str]] = None
    functional_areas: Optional[List[dict]] = None
    target_go_live: Optional[str] = None
    lead_name: Optional[str] = None


# =============================================================================
# CRUD ENDPOINTS
# =============================================================================

@router.get("/list")
async def list_customers():
    """Get all customers"""
    try:
        customers = ProjectModel.get_all(status='active')
        
        # Format for frontend
        formatted = []
        for cust in customers:
            metadata = cust.get('metadata', {})
            
            formatted.append({
                'id': cust.get('id'),  # THE identifier
                'name': cust.get('name'),  # Display name
                'product': metadata.get('product', ''),
                'engagement_types': metadata.get('engagement_types', ['Implementation']),
                'start_date': cust.get('start_date'),
                'status': cust.get('status', 'active'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),
                'systems': metadata.get('systems', []),
                'domains': metadata.get('domains', []),
                'functional_areas': metadata.get('functional_areas', []),
                'target_go_live': metadata.get('target_go_live', ''),
                'lead_name': metadata.get('lead_name', ''),
                'created_at': cust.get('created_at'),
                'updated_at': cust.get('updated_at'),
                'created_by': cust.get('created_by'),
                'metadata': metadata,
                # DEPRECATED fields for backward compatibility
                'customer': cust.get('name'),  # Old field name
                'code': cust.get('id'),  # Maps to id now
                'type': metadata.get('engagement_types', ['Implementation'])[0] if metadata.get('engagement_types') else 'Implementation',
            })
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error listing customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_customer(customer: CustomerCreate):
    """Create a new customer"""
    try:
        logger.info(f"Creating customer: {customer.name}")
        
        new_customer = ProjectModel.create(
            name=customer.name,
            engagement_types=customer.engagement_types,
            notes=customer.notes or "",
            product=customer.product or ""
        )
        
        if not new_customer:
            raise HTTPException(status_code=500, detail="Failed to create customer")
        
        # Update metadata with all additional fields
        existing_metadata = new_customer.get('metadata', {})
        
        if customer.playbooks:
            existing_metadata['playbooks'] = customer.playbooks
        if customer.systems:
            existing_metadata['systems'] = customer.systems
        if customer.domains:
            existing_metadata['domains'] = customer.domains
        if customer.functional_areas:
            existing_metadata['functional_areas'] = customer.functional_areas
        if customer.target_go_live:
            existing_metadata['target_go_live'] = customer.target_go_live
        if customer.lead_name:
            existing_metadata['lead_name'] = customer.lead_name
        
        # Save updated metadata
        ProjectModel.update(new_customer['id'], metadata=existing_metadata)
        new_customer['metadata'] = existing_metadata
        
        metadata = new_customer.get('metadata', {})
        
        return {
            "success": True,
            "customer": {
                'id': new_customer.get('id'),  # THE identifier
                'name': new_customer.get('name'),
                'product': metadata.get('product', ''),
                'engagement_types': metadata.get('engagement_types', ['Implementation']),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),
                'systems': metadata.get('systems', []),
                'domains': metadata.get('domains', []),
                'functional_areas': metadata.get('functional_areas', []),
                'target_go_live': metadata.get('target_go_live', ''),
                'lead_name': metadata.get('lead_name', ''),
                'status': new_customer.get('status', 'active'),
                'created_at': new_customer.get('created_at'),
                # DEPRECATED fields
                'customer': new_customer.get('name'),
                'code': new_customer.get('id'),
            },
            # Also return as 'project' for backward compatibility
            "project": {
                'id': new_customer.get('id'),
                'name': new_customer.get('name'),
                'code': new_customer.get('id'),
                'customer': new_customer.get('name'),
            },
            "message": f"Customer '{customer.name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{customer_id}")
async def update_customer(customer_id: str, updates: CustomerUpdate):
    """Update customer"""
    try:
        logger.info(f"Updating customer {customer_id}")
        
        update_dict = {}
        
        # Direct column updates
        if updates.name is not None:
            update_dict['name'] = updates.name
        
        if updates.status is not None:
            update_dict['status'] = updates.status
        
        if updates.start_date is not None:
            update_dict['start_date'] = updates.start_date
        
        # Metadata updates
        metadata_fields_present = any([
            updates.engagement_types is not None,
            updates.notes is not None,
            updates.product is not None,
            updates.playbooks is not None,
            updates.systems is not None,
            updates.domains is not None,
            updates.functional_areas is not None,
            updates.target_go_live is not None,
            updates.lead_name is not None,
        ])
        
        if metadata_fields_present:
            existing = ProjectModel.get_by_id(customer_id)
            if existing:
                existing_metadata = existing.get('metadata', {})
                
                if updates.engagement_types is not None:
                    existing_metadata['engagement_types'] = updates.engagement_types
                if updates.notes is not None:
                    existing_metadata['notes'] = updates.notes
                if updates.product is not None:
                    existing_metadata['product'] = updates.product
                if updates.playbooks is not None:
                    existing_metadata['playbooks'] = updates.playbooks
                if updates.systems is not None:
                    existing_metadata['systems'] = updates.systems
                if updates.domains is not None:
                    existing_metadata['domains'] = updates.domains
                if updates.functional_areas is not None:
                    existing_metadata['functional_areas'] = updates.functional_areas
                if updates.target_go_live is not None:
                    existing_metadata['target_go_live'] = updates.target_go_live
                if updates.lead_name is not None:
                    existing_metadata['lead_name'] = updates.lead_name
                
                update_dict['metadata'] = existing_metadata
        
        updated = ProjectModel.update(customer_id, **update_dict)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        metadata = updated.get('metadata', {})
        
        return {
            "success": True,
            "customer": {
                'id': updated.get('id'),
                'name': updated.get('name'),
                'product': metadata.get('product', ''),
                'engagement_types': metadata.get('engagement_types', ['Implementation']),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),
                'systems': metadata.get('systems', []),
                'domains': metadata.get('domains', []),
                'functional_areas': metadata.get('functional_areas', []),
                'target_go_live': metadata.get('target_go_live', ''),
                'lead_name': metadata.get('lead_name', ''),
                'status': updated.get('status', 'active'),
                'updated_at': updated.get('updated_at'),
            },
            "message": "Customer updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    """Delete customer (soft delete)"""
    try:
        logger.info(f"Deleting customer {customer_id}")
        
        success = ProjectModel.delete(customer_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        return {
            "success": True,
            "message": "Customer deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    """Get single customer by ID"""
    try:
        customer = ProjectModel.get_by_id(customer_id)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        metadata = customer.get('metadata', {})
        
        return {
            'id': customer.get('id'),
            'name': customer.get('name'),
            'product': metadata.get('product', ''),
            'engagement_types': metadata.get('engagement_types', ['Implementation']),
            'notes': metadata.get('notes', ''),
            'playbooks': metadata.get('playbooks', []),
            'status': customer.get('status', 'active'),
            'start_date': customer.get('start_date'),
            'created_at': customer.get('created_at'),
            'updated_at': customer.get('updated_at'),
            # DEPRECATED
            'customer': customer.get('name'),
            'code': customer.get('id'),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DATA OPERATIONS (reprofile, recalc, term-index, resolve-terms)
# These operate on a customer's data using customer_id
# =============================================================================

class RecalcRequest(BaseModel):
    """Schema for recalc request"""
    what: Optional[List[str]] = ["terms", "entities", "joins"]


@router.post("/{customer_id}/reprofile")
async def reprofile_customer_columns(customer_id: str):
    """
    Re-run filter category detection on existing column profiles.
    
    This is needed when column profiles were created before the term index
    was implemented. After reprofiling, run /recalc to populate the term index.
    """
    try:
        from utils.structured_data_handler import StructuredDataHandler
        import json
        
        logger.info(f"Reprofiling columns for customer {customer_id}")
        
        handler = StructuredDataHandler()
        conn = handler.conn
        
        # Get all column profiles for this customer
        profiles = conn.execute("""
            SELECT table_name, column_name, distinct_count, distinct_values, inferred_type
            FROM _column_profiles
            WHERE project = ?
        """, [customer_id]).fetchall()
        
        stats = {
            'total_columns': len(profiles),
            'reprofiled': 0,
            'location': 0,
            'status': 0,
            'company': 0,
            'organization': 0,
            'job': 0,
            'pay_type': 0,
            'employee_type': 0,
            'skipped': 0
        }
        
        for row in profiles:
            table_name, column_name, distinct_count, distinct_values_json, inferred_type = row
            
            if not distinct_values_json or not distinct_count or distinct_count > 500:
                stats['skipped'] += 1
                continue
            
            try:
                distinct_values = json.loads(distinct_values_json) if isinstance(distinct_values_json, str) else distinct_values_json
            except:
                stats['skipped'] += 1
                continue
            
            if not distinct_values:
                stats['skipped'] += 1
                continue
            
            profile = {
                'distinct_count': distinct_count,
                'inferred_type': inferred_type,
                'filter_category': None,
                'filter_priority': 0
            }
            
            updated_profile = handler._detect_filter_category(column_name, profile, distinct_values, customer_id)
            
            if updated_profile.get('filter_category'):
                conn.execute("""
                    UPDATE _column_profiles 
                    SET filter_category = ?, filter_priority = ?
                    WHERE project = ? AND table_name = ? AND column_name = ?
                """, [
                    updated_profile['filter_category'],
                    updated_profile.get('filter_priority', 0),
                    customer_id,
                    table_name,
                    column_name
                ])
                
                stats['reprofiled'] += 1
                category = updated_profile['filter_category']
                if category in stats:
                    stats[category] += 1
                
                logger.debug(f"[REPROFILE] {table_name}.{column_name} → {category}")
        
        conn.commit()
        
        logger.info(f"Reprofiled {stats['reprofiled']} columns for {customer_id}: {stats}")
        
        return {
            "success": True,
            "customer_id": customer_id,
            "stats": stats,
            "message": f"Reprofiled {stats['reprofiled']} columns. Run /recalc to populate term index."
        }
        
    except Exception as e:
        logger.error(f"Error reprofiling columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{customer_id}/recalc")
async def recalc_customer_indexes(customer_id: str, request: RecalcRequest = None):
    """
    Recalculate load-time indexes for a customer without re-uploading files.
    
    Rebuilds: term index, entity tables, join priorities
    """
    try:
        from utils.structured_data_handler import StructuredDataHandler
        from backend.utils.intelligence.term_index import recalc_term_index
        
        what = request.what if request else ["terms", "entities", "joins"]
        
        logger.info(f"Recalculating indexes for customer {customer_id}: {what}")
        
        handler = StructuredDataHandler()
        
        # Diagnostic
        diag_profiles = handler.conn.execute("""
            SELECT filter_category, COUNT(*) as cnt,
                   SUM(CASE WHEN distinct_values IS NOT NULL THEN 1 ELSE 0 END) as with_values
            FROM _column_profiles
            WHERE project = ? AND filter_category IS NOT NULL
            GROUP BY filter_category
        """, [customer_id]).fetchall()
        
        diagnostics = {
            'profiles_by_category': {row[0]: {'count': row[1], 'with_values': row[2]} for row in diag_profiles}
        }
        
        results = {}
        
        if "all" in what or "terms" in what or "entities" in what or "joins" in what:
            stats = recalc_term_index(handler.conn, customer_id)
            results = stats
        
        return {
            "success": True,
            "customer_id": customer_id,
            "recalculated": what,
            "stats": results,
            "diagnostics": diagnostics,
            "message": "Index recalculation complete"
        }
        
    except ImportError as e:
        logger.warning(f"Term index module not available: {e}")
        return {
            "success": False,
            "error": "Term index module not available",
            "message": "This feature requires the term_index module to be installed"
        }
    except Exception as e:
        logger.error(f"Error recalculating indexes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{customer_id}/term-index")
async def get_term_index_contents(customer_id: str, term: str = None, limit: int = 50):
    """Diagnostic endpoint to see what's in the term index."""
    try:
        from utils.structured_data_handler import StructuredDataHandler
        
        handler = StructuredDataHandler()
        conn = handler.conn
        
        if term:
            results = conn.execute("""
                SELECT term, term_type, table_name, column_name, operator, match_value, 
                       domain, entity, confidence, source
                FROM _term_index
                WHERE project = ? AND term LIKE ?
                ORDER BY confidence DESC
                LIMIT ?
            """, [customer_id, f'%{term.lower()}%', limit]).fetchall()
        else:
            results = conn.execute("""
                SELECT term, term_type, table_name, column_name, operator, match_value, 
                       domain, entity, confidence, source
                FROM _term_index
                WHERE project = ?
                ORDER BY term
                LIMIT ?
            """, [customer_id, limit]).fetchall()
        
        location_profiles = conn.execute("""
            SELECT table_name, column_name, distinct_count, distinct_values
            FROM _column_profiles
            WHERE project = ? AND filter_category = 'location'
            LIMIT 10
        """, [customer_id]).fetchall()
        
        return {
            "success": True,
            "customer_id": customer_id,
            "search_term": term,
            "terms": [
                {
                    "term": r[0],
                    "term_type": r[1],
                    "table": r[2],
                    "column": r[3],
                    "operator": r[4],
                    "match_value": r[5],
                    "domain": r[6],
                    "entity": r[7],
                    "confidence": r[8],
                    "source": r[9]
                }
                for r in results
            ],
            "location_profiles": [
                {
                    "table": r[0],
                    "column": r[1],
                    "distinct_count": r[2],
                    "sample_values": r[3][:200] if r[3] else None
                }
                for r in location_profiles
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting term index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PRODUCT REGISTRY ENDPOINTS
# These don't change - they're about products, not customers
# =============================================================================

try:
    from backend.utils.products import (
        get_registry, 
        get_product,
        list_products_by_category,
        compare_schemas,
        quick_compare,
    )
    PRODUCTS_AVAILABLE = True
except ImportError:
    PRODUCTS_AVAILABLE = False
    logger.warning("[CUSTOMERS] Product registry not available")


@router.get("/products/list")
async def list_products():
    """List all available products for customer setup."""
    if not PRODUCTS_AVAILABLE:
        return {"products": [], "categories": [], "error": "Product registry not available"}
    
    try:
        registry = get_registry()
        registry.load()
        
        categories = {}
        for product in registry.list_all():
            cat = product.category
            if cat not in categories:
                categories[cat] = []
            
            categories[cat].append({
                "id": product.product_id,
                "name": product.product,
                "vendor": product.vendor,
                "hub_count": product.hub_count,
                "domain_count": product.domain_count,
            })
        
        for cat in categories:
            categories[cat] = sorted(categories[cat], key=lambda x: (x["vendor"], x["name"]))
        
        return {
            "products": categories,
            "categories": sorted(categories.keys()),
            "total": sum(len(v) for v in categories.values()),
        }
        
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/categories")
async def list_product_categories():
    """List all product categories with counts."""
    if not PRODUCTS_AVAILABLE:
        return {"categories": []}
    
    try:
        registry = get_registry()
        summary = registry.summary()
        
        return {
            "categories": [
                {"name": cat, "count": count}
                for cat, count in sorted(summary["by_category"].items())
            ],
            "vendors": [
                {"name": vendor, "count": count}
                for vendor, count in sorted(summary["by_vendor"].items(), key=lambda x: -x[1])
            ][:15],
            "total_products": summary["total_products"],
            "total_hubs": summary["total_hubs"],
        }
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}")
async def get_product_details(product_id: str):
    """Get detailed information about a specific product."""
    if not PRODUCTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Product registry not available")
    
    try:
        product = get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")
        
        return {
            "product_id": product.product_id,
            "vendor": product.vendor,
            "name": product.product,
            "category": product.category,
            "version": product.version,
            "api_types": product.api_types,
            "product_focus": product.product_focus,
            "domain_count": product.domain_count,
            "hub_count": product.hub_count,
            "domains": {
                name: {
                    "description": d.description,
                    "hub_count": d.hub_count,
                    "hubs": d.hubs,
                }
                for name, d in product.domains.items()
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/compare/{source_id}/{target_id}")
async def compare_products(source_id: str, target_id: str):
    """Compare two product schemas for M&A integration analysis."""
    if not PRODUCTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Product registry not available")
    
    try:
        result = compare_schemas(source_id, target_id)
        
        return {
            "source": {
                "product_id": source_id,
                "vendor": result.source_vendor,
                "name": result.source_product,
                "hub_count": result.total_source_hubs,
            },
            "target": {
                "product_id": target_id,
                "vendor": result.target_vendor,
                "name": result.target_product,
                "hub_count": result.total_target_hubs,
            },
            "scores": {
                "compatibility": round(result.compatibility_score * 100),
                "complexity": round(result.complexity_score * 100),
                "risk": round(result.risk_score * 100),
            },
            "analysis": {
                "total_domains": result.total_domains,
                "matched_domains": result.matched_domains,
                "partial_domains": result.partial_domains,
                "source_only_domains": result.source_only_domains,
                "target_only_domains": result.target_only_domains,
                "matched_hubs": result.matched_hubs,
            },
            "recommendations": result.integration_recommendations,
            "risks": result.risk_factors,
            "summary_markdown": result.summary(),
            "gap_analysis_markdown": result.gap_analysis(),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
