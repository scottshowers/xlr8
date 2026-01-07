"""
Entity Registry - Unified Entity Tracking Across Storage Systems
================================================================

Phase 8A: Tracks all known entity types (hubs) across DuckDB and ChromaDB.

This enables:
- "What do we know about earnings_code?" → returns DuckDB tables + ChromaDB docs
- Cross-storage gap detection
- Unified context graph API

Tables (in Supabase):
- entity_registry: Master list of entity types
- entity_references: Where each entity appears

Deploy to: backend/utils/entity_registry.py
"""

import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Supabase client
_supabase = None

def _get_supabase():
    """Get or create Supabase client."""
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                _supabase = create_client(url, key)
                logger.info("[ENTITY_REGISTRY] Supabase client initialized")
            else:
                logger.warning("[ENTITY_REGISTRY] Supabase credentials not found")
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to init Supabase: {e}")
    return _supabase


class EntityRegistry:
    """
    Unified registry for tracking entities across DuckDB and ChromaDB.
    
    Usage:
        registry = EntityRegistry()
        
        # Register a DuckDB hub
        registry.register_duckdb_hub(
            entity_type="earnings_code",
            project_id="TEA1000",
            table_name="earnings_codes",
            column_name="code",
            value_count=45
        )
        
        # Register a ChromaDB mention
        registry.register_chromadb_mention(
            entity_type="earnings_code",
            document_id="abc123",
            document_name="Earnings Guide.pdf",
            chunk_count=5,
            confidence=0.85
        )
        
        # Query unified view
        info = registry.get_entity_info("earnings_code")
        gaps = registry.get_gaps()
    """
    
    def __init__(self):
        """Initialize the registry."""
        self.supabase = _get_supabase()
        if not self.supabase:
            logger.warning("[ENTITY_REGISTRY] Running without Supabase - data won't persist")
    
    # =========================================================================
    # REGISTRATION METHODS
    # =========================================================================
    
    def ensure_entity_exists(
        self,
        entity_type: str,
        display_name: Optional[str] = None,
        category: Optional[str] = None,
        source: str = "duckdb",
        is_discovered: bool = True
    ) -> bool:
        """
        Ensure an entity type exists in the registry.
        Creates it if it doesn't exist.
        
        Returns True if created, False if already existed.
        """
        if not self.supabase:
            return False
        
        try:
            # Check if exists
            result = self.supabase.table('entity_registry').select('entity_type').eq('entity_type', entity_type).execute()
            
            if result.data:
                return False  # Already exists
            
            # Create new entry
            if not display_name:
                # Convert snake_case to Title Case
                display_name = entity_type.replace('_', ' ').title()
            
            if not category:
                # Infer category from entity type
                category = self._infer_category(entity_type)
            
            self.supabase.table('entity_registry').insert({
                'entity_type': entity_type,
                'display_name': display_name,
                'category': category,
                'source': source,
                'is_discovered': is_discovered
            }).execute()
            
            logger.info(f"[ENTITY_REGISTRY] Created new entity: {entity_type} (source={source})")
            return True
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to ensure entity {entity_type}: {e}")
            return False
    
    def register_duckdb_hub(
        self,
        entity_type: str,
        project_id: str,
        table_name: str,
        column_name: str,
        value_count: int = 0,
        display_name: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """Register a DuckDB table/column as a hub for an entity type."""
        if not self.supabase:
            return False
        
        try:
            # Ensure entity exists
            self.ensure_entity_exists(entity_type, display_name, category, source="duckdb")
            
            # Upsert reference
            self.supabase.table('entity_references').upsert({
                'entity_type': entity_type,
                'storage_type': 'duckdb',
                'project_id': project_id,
                'reference_type': 'hub',
                'table_name': table_name,
                'column_name': column_name,
                'value_count': value_count,
                'confidence': 1.0
            }, on_conflict='entity_type,storage_type,project_id,table_name,column_name').execute()
            
            # Update aggregate stats
            self._update_entity_stats(entity_type)
            
            logger.debug(f"[ENTITY_REGISTRY] Registered DuckDB hub: {entity_type} @ {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to register DuckDB hub: {e}")
            return False
    
    def register_duckdb_spoke(
        self,
        entity_type: str,
        project_id: str,
        table_name: str,
        column_name: str,
        value_count: int = 0,
        coverage_pct: float = 0.0
    ) -> bool:
        """Register a DuckDB table/column as a spoke referencing an entity type."""
        if not self.supabase:
            return False
        
        try:
            # Ensure entity exists (spoke shouldn't create new entities usually)
            self.ensure_entity_exists(entity_type, source="duckdb")
            
            # Upsert reference
            self.supabase.table('entity_references').upsert({
                'entity_type': entity_type,
                'storage_type': 'duckdb',
                'project_id': project_id,
                'reference_type': 'spoke',
                'table_name': table_name,
                'column_name': column_name,
                'value_count': value_count,
                'coverage_pct': coverage_pct,
                'confidence': 1.0
            }, on_conflict='entity_type,storage_type,project_id,table_name,column_name').execute()
            
            # Update aggregate stats
            self._update_entity_stats(entity_type)
            
            logger.debug(f"[ENTITY_REGISTRY] Registered DuckDB spoke: {entity_type} @ {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to register DuckDB spoke: {e}")
            return False
    
    def register_chromadb_mention(
        self,
        entity_type: str,
        document_id: str,
        document_name: str,
        project_id: Optional[str] = None,
        chunk_count: int = 1,
        confidence: float = 1.0
    ) -> bool:
        """Register a ChromaDB document as mentioning an entity type."""
        if not self.supabase:
            return False
        
        try:
            # Ensure entity exists
            self.ensure_entity_exists(entity_type, source="chromadb")
            
            # Use __STANDARDS__ for global docs
            if not project_id:
                project_id = "__STANDARDS__"
            
            # Upsert reference
            self.supabase.table('entity_references').upsert({
                'entity_type': entity_type,
                'storage_type': 'chromadb',
                'project_id': project_id,
                'reference_type': 'mention',
                'document_id': document_id,
                'document_name': document_name,
                'chunk_count': chunk_count,
                'confidence': confidence
            }, on_conflict='entity_type,storage_type,project_id,document_id').execute()
            
            # Update aggregate stats
            self._update_entity_stats(entity_type)
            
            logger.debug(f"[ENTITY_REGISTRY] Registered ChromaDB mention: {entity_type} @ {document_name}")
            return True
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to register ChromaDB mention: {e}")
            return False
    
    def register_chromadb_mentions_batch(
        self,
        document_id: str,
        document_name: str,
        hub_references: List[str],
        project_id: Optional[str] = None,
        confidence: float = 1.0
    ) -> int:
        """Register multiple entity mentions from a single document."""
        count = 0
        for entity_type in hub_references:
            if self.register_chromadb_mention(
                entity_type=entity_type,
                document_id=document_id,
                document_name=document_name,
                project_id=project_id,
                confidence=confidence
            ):
                count += 1
        return count
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_entity_info(self, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive info about an entity type.
        
        Returns:
            {
                "entity_type": "earnings_code",
                "display_name": "Earnings Code",
                "category": "payroll",
                "total_values": 45,
                "duckdb_hubs": [...],
                "duckdb_spokes": [...],
                "chromadb_docs": [...]
            }
        """
        if not self.supabase:
            return None
        
        try:
            # Get entity info
            entity_result = self.supabase.table('entity_registry').select('*').eq('entity_type', entity_type).execute()
            
            if not entity_result.data:
                return None
            
            entity = entity_result.data[0]
            
            # Get references
            refs_result = self.supabase.table('entity_references').select('*').eq('entity_type', entity_type).execute()
            
            refs = refs_result.data or []
            
            return {
                "entity_type": entity['entity_type'],
                "display_name": entity['display_name'],
                "category": entity['category'],
                "source": entity['source'],
                "is_discovered": entity['is_discovered'],
                "total_values": entity['total_values'],
                "duckdb_references": entity['duckdb_references'],
                "chromadb_references": entity['chromadb_references'],
                "duckdb_hubs": [r for r in refs if r['storage_type'] == 'duckdb' and r['reference_type'] == 'hub'],
                "duckdb_spokes": [r for r in refs if r['storage_type'] == 'duckdb' and r['reference_type'] == 'spoke'],
                "chromadb_docs": [r for r in refs if r['storage_type'] == 'chromadb']
            }
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to get entity info: {e}")
            return None
    
    def get_all_entities(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all registered entity types."""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table('entity_registry').select('*').order('entity_type')
            
            if category:
                query = query.eq('category', category)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to get entities: {e}")
            return []
    
    def get_entity_summary(self) -> List[Dict[str, Any]]:
        """Get summary view of all entities with reference counts."""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('entity_summary').select('*').execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to get summary: {e}")
            return []
    
    def get_gaps(self) -> List[Dict[str, Any]]:
        """Get entities with gaps (docs but no config, or vice versa)."""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('entity_gaps').select('*').execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to get gaps: {e}")
            return []
    
    def get_references_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all entity references for a specific project."""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table('entity_references').select('*').eq('project_id', project_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to get project refs: {e}")
            return []
    
    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """Search entities by type or display name."""
        if not self.supabase:
            return []
        
        try:
            # Search both entity_type and display_name
            result = self.supabase.table('entity_registry').select('*').or_(
                f"entity_type.ilike.%{query}%,display_name.ilike.%{query}%"
            ).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to search: {e}")
            return []
    
    # =========================================================================
    # CLEANUP METHODS
    # =========================================================================
    
    def remove_duckdb_references(self, project_id: str, table_name: Optional[str] = None) -> int:
        """Remove DuckDB references for a project (or specific table)."""
        if not self.supabase:
            return 0
        
        try:
            query = self.supabase.table('entity_references').delete().eq('storage_type', 'duckdb').eq('project_id', project_id)
            
            if table_name:
                query = query.eq('table_name', table_name)
            
            result = query.execute()
            count = len(result.data) if result.data else 0
            logger.info(f"[ENTITY_REGISTRY] Removed {count} DuckDB references for {project_id}")
            return count
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to remove DuckDB refs: {e}")
            return 0
    
    def remove_chromadb_references(self, document_id: str) -> int:
        """Remove ChromaDB references for a document."""
        if not self.supabase:
            return 0
        
        try:
            result = self.supabase.table('entity_references').delete().eq('storage_type', 'chromadb').eq('document_id', document_id).execute()
            count = len(result.data) if result.data else 0
            logger.info(f"[ENTITY_REGISTRY] Removed {count} ChromaDB references for {document_id}")
            return count
            
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to remove ChromaDB refs: {e}")
            return 0
    
    def clear_all(self) -> Dict[str, int]:
        """Nuclear option: Clear all references (but keep entity definitions)."""
        if not self.supabase:
            return {"references": 0}
        
        try:
            result = self.supabase.table('entity_references').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            count = len(result.data) if result.data else 0
            logger.warning(f"[ENTITY_REGISTRY] Cleared {count} references")
            return {"references": count}
        except Exception as e:
            logger.error(f"[ENTITY_REGISTRY] Failed to clear: {e}")
            return {"references": 0, "error": str(e)}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _infer_category(self, entity_type: str) -> str:
        """Infer category from entity type name."""
        entity_lower = entity_type.lower()
        
        if any(x in entity_lower for x in ['earning', 'deduction', 'pay', 'wage', 'salary', 'gl', 'shift']):
            return 'payroll'
        elif any(x in entity_lower for x in ['tax', 'withhold', 'w2', 'w4']):
            return 'tax'
        elif any(x in entity_lower for x in ['benefit', 'accrual', 'pto', 'leave', '401k', 'health']):
            return 'benefits'
        elif any(x in entity_lower for x in ['job', 'department', 'location', 'company', 'employee', 'position', 'org']):
            return 'hr'
        else:
            return 'general'
    
    def _update_entity_stats(self, entity_type: str) -> None:
        """Update aggregate stats for an entity."""
        if not self.supabase:
            return
        
        try:
            # Count references by storage type
            refs = self.supabase.table('entity_references').select('storage_type').eq('entity_type', entity_type).execute()
            
            duckdb_count = sum(1 for r in (refs.data or []) if r['storage_type'] == 'duckdb')
            chromadb_count = sum(1 for r in (refs.data or []) if r['storage_type'] == 'chromadb')
            
            # Update registry
            self.supabase.table('entity_registry').update({
                'duckdb_references': duckdb_count,
                'chromadb_references': chromadb_count
            }).eq('entity_type', entity_type).execute()
            
        except Exception as e:
            logger.debug(f"[ENTITY_REGISTRY] Failed to update stats: {e}")


# Module-level singleton
_registry: Optional[EntityRegistry] = None

def get_entity_registry() -> EntityRegistry:
    """Get the singleton EntityRegistry instance."""
    global _registry
    if _registry is None:
        _registry = EntityRegistry()
    return _registry
