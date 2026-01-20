"""
XLR8 Intelligence Engine - Configuration Gatherer
==================================================

Gathers CONFIGURATION truths - how the customer configured their system.

v6.0 REWRITE: Uses Context Graph LOOKUPS, not TableSelector scoring.

The Context Graph already knows which config tables relate to which reality tables.
We don't score. We don't guess. We LOOKUP.

Algorithm:
1. Get reality table from QueryResolver context
2. LOOKUP Context Graph relationships where spoke_table = reality_table
3. Return those config hubs with their pre-computed coverage/gap data

Storage: DuckDB (structured queries)
Source: Config tables (code tables, mappings, system setup)
Scope: Project-scoped

Deploy to: backend/utils/intelligence/gatherers/configuration.py
"""

import logging
from typing import Dict, List, Optional, Any

from .base import DuckDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class ConfigurationGatherer(DuckDBGatherer):
    """
    Gathers Configuration truths from DuckDB using Context Graph LOOKUPS.
    
    v6.0: No more TableSelector scoring. Pure lookups against pre-computed
    hub/spoke relationships from the Context Graph.
    
    The Context Graph tells us:
    - Which config tables (hubs) relate to which reality tables (spokes)
    - How many values are configured (hub_cardinality)
    - How many values are in use (spoke_cardinality)  
    - The gap percentage (coverage_pct)
    
    This is the $500/hr insight: "5 configured, 3 in use, 2 are dead weight"
    """
    
    truth_type = TruthType.CONFIGURATION
    
    def __init__(self, project_name: str, customer_id: str = None,
                 structured_handler=None, schema: Dict = None,
                 table_selector=None):
        """
        Initialize Configuration gatherer.
        
        Args:
            project_name: Project code
            customer_id: Project UUID
            structured_handler: DuckDB handler (has get_context_graph)
            schema: Schema metadata (tables, columns) - used as fallback
            table_selector: TableSelector instance - NOT USED in v6.0, kept for interface compatibility
        """
        super().__init__(project_name, customer_id, structured_handler)
        self.schema = schema or {}
        # table_selector kept for interface compatibility but not used
        self.table_selector = table_selector
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Configuration truths for the question.
        
        v6.0: Uses Context Graph to find related config tables.
        
        Args:
            question: User's question
            context: Analysis context (must contain 'resolver' with table_name)
            
        Returns:
            List of Truth objects from config tables with gap analysis
        """
        self.log_gather_start(question)
        
        if not self.handler:
            logger.debug("[GATHER-CONFIG] No handler available")
            return []
        
        truths = []
        
        try:
            # STEP 1: Find related config tables via Context Graph LOOKUP
            config_tables = self._find_related_configs(context)
            
            if not config_tables:
                logger.warning("[GATHER-CONFIG] No related config tables found in Context Graph")
                return []
            
            logger.warning(f"[GATHER-CONFIG] Found {len(config_tables)} related config tables via Context Graph")
            
            # STEP 2: Query each config table and include gap data
            for config_info in config_tables:
                truth = self._query_config_table(config_info)
                if truth:
                    truths.append(truth)
                    
        except Exception as e:
            logger.error(f"[GATHER-CONFIG] Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        self.log_gather_result(truths)
        return truths
    
    def _find_related_configs(self, context: Dict) -> List[Dict]:
        """
        Find config tables related to the reality table via Context Graph LOOKUP.
        
        NO SCORING. NO NAME MATCHING. PURE LOOKUP.
        
        The Context Graph already computed these relationships at upload time.
        We just read them.
        
        Args:
            context: Must contain 'resolver' with 'table_name' (the reality table)
            
        Returns:
            List of config table info dicts with gap data
        """
        # Get the reality table from QueryResolver
        resolver = context.get('resolver', {})
        reality_table = resolver.get('table_name')
        
        if not reality_table:
            logger.warning("[GATHER-CONFIG] No reality table in resolver context")
            return []
        
        logger.warning(f"[GATHER-CONFIG] Looking up configs related to reality table: {reality_table[:60]}...")
        
        # LOOKUP: Get Context Graph
        if not hasattr(self.handler, 'get_context_graph'):
            logger.error("[GATHER-CONFIG] Handler missing get_context_graph method")
            return []
        
        graph = self.handler.get_context_graph(self.project_name)
        
        if not graph:
            logger.warning("[GATHER-CONFIG] No context graph available")
            return []
        
        relationships = graph.get('relationships', [])
        hubs = graph.get('hubs', [])
        
        logger.warning(f"[GATHER-CONFIG] Context Graph has {len(hubs)} hubs, {len(relationships)} relationships")
        
        # LOOKUP: Find all config hubs where this reality table is a spoke
        related_configs = []
        seen_hubs = set()  # Dedupe by hub table
        
        for rel in relationships:
            spoke_table = rel.get('spoke_table', '')
            hub_table = rel.get('hub_table', '')
            truth_type = rel.get('truth_type', '')
            
            # Match: This reality table references this hub
            # We want relationships where OUR reality table is the spoke
            if spoke_table.lower() == reality_table.lower():
                
                # Skip if we've already added this hub
                if hub_table.lower() in seen_hubs:
                    continue
                seen_hubs.add(hub_table.lower())
                
                # Get hub metadata
                hub_info = self._get_hub_info(hubs, rel.get('semantic_type'))
                
                config_info = {
                    'hub_table': hub_table,
                    'hub_column': rel.get('hub_column'),
                    'semantic_type': rel.get('semantic_type'),
                    'hub_cardinality': rel.get('hub_cardinality', 0),      # Configured count
                    'spoke_cardinality': rel.get('spoke_cardinality', 0),  # In-use count
                    'coverage_pct': rel.get('coverage_pct', 0),            # Gap percentage
                    'is_valid_fk': rel.get('is_valid_fk', False),
                    'hub_truth_type': hub_info.get('truth_type', 'configuration') if hub_info else 'configuration',
                    'hub_entity_type': hub_info.get('entity_type') if hub_info else None,
                    'hub_category': hub_info.get('category') if hub_info else None,
                }
                
                related_configs.append(config_info)
                
                logger.info(f"[GATHER-CONFIG] Found related config: {rel.get('semantic_type')} -> "
                           f"{hub_table} ({rel.get('spoke_cardinality', 0)}/{rel.get('hub_cardinality', 0)} = "
                           f"{rel.get('coverage_pct', 0):.1f}% coverage)")
        
        # Sort by coverage_pct ascending (lowest coverage = biggest gap = most interesting)
        related_configs.sort(key=lambda x: x.get('coverage_pct', 100))
        
        logger.warning(f"[GATHER-CONFIG] Found {len(related_configs)} related configs: "
                      f"{[c['semantic_type'] for c in related_configs[:5]]}")
        
        return related_configs
    
    def _get_hub_info(self, hubs: List[Dict], semantic_type: str) -> Optional[Dict]:
        """Get hub metadata by semantic type."""
        if not semantic_type:
            return None
        for hub in hubs:
            if hub.get('semantic_type') == semantic_type:
                return hub
        return None
    
    def _query_config_table(self, config_info: Dict) -> Optional[Truth]:
        """
        Query a config table and return as Truth with gap analysis.
        
        The gap data (configured vs in-use) is ALREADY COMPUTED in config_info.
        We just query the actual config values and attach the gap analysis.
        """
        hub_table = config_info.get('hub_table')
        if not hub_table:
            return None
        
        try:
            # Query the config table (these are small - usually < 100 rows)
            sql = f'SELECT * FROM "{hub_table}" LIMIT 100'
            rows = self.handler.query(sql)
            
            if not rows:
                logger.debug(f"[GATHER-CONFIG] No rows in {hub_table}")
                return None
            
            columns = list(rows[0].keys()) if rows else []
            
            # Build display name from semantic type
            semantic_type = config_info.get('semantic_type', hub_table)
            display_name = semantic_type.replace('_', ' ').title()
            
            # THE KEY INSIGHT: Include pre-computed gap analysis
            gap_analysis = {
                'configured_count': config_info.get('hub_cardinality', 0),
                'in_use_count': config_info.get('spoke_cardinality', 0),
                'coverage_pct': config_info.get('coverage_pct', 0),
                'unused_count': config_info.get('hub_cardinality', 0) - config_info.get('spoke_cardinality', 0),
                'is_valid_fk': config_info.get('is_valid_fk', False),
            }
            
            # Log the gap for visibility
            if gap_analysis['unused_count'] > 0:
                logger.warning(f"[GATHER-CONFIG] GAP DETECTED: {semantic_type} has "
                              f"{gap_analysis['unused_count']} configured but unused values "
                              f"({gap_analysis['in_use_count']}/{gap_analysis['configured_count']} in use)")
            
            return self.create_truth(
                source_name=display_name,
                content={
                    'sql': sql,
                    'columns': columns,
                    'rows': rows,
                    'total': len(rows),
                    'table': hub_table,
                    'display_name': display_name,
                    'is_config_table': True,
                    'semantic_type': semantic_type,
                    'hub_column': config_info.get('hub_column'),
                    'entity_type': config_info.get('hub_entity_type'),
                    'category': config_info.get('hub_category'),
                    # THE GAP ANALYSIS - pre-computed, not re-calculated
                    'gap_analysis': gap_analysis,
                },
                location=f"Config table: {display_name}",
                confidence=0.95,  # High confidence - these are direct lookups
                row_count=len(rows),
                column_count=len(columns),
                domain=config_info.get('hub_category')
            )
            
        except Exception as e:
            logger.error(f"[GATHER-CONFIG] Error querying {hub_table}: {e}")
            return None
