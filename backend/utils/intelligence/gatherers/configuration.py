"""
XLR8 Intelligence Engine - Configuration Gatherer
==================================================

Gathers CONFIGURATION truths - how the customer configured their system.

Storage: DuckDB (structured queries)
Source: Config tables (code tables, mappings, system setup)
Scope: Project-scoped

NOTE: This queries DuckDB config tables, NOT ChromaDB documents.
Per ARCHITECTURE.md: Configuration = DuckDB = "Code tables, mappings, system setup"

Deploy to: backend/utils/intelligence/gatherers/configuration.py
"""

import logging
from typing import Dict, List, Optional, Any

from .base import DuckDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class ConfigurationGatherer(DuckDBGatherer):
    """
    Gathers Configuration truths from DuckDB.
    
    Configuration represents how the system is set up:
    - Earnings codes
    - Deduction codes
    - Tax codes
    - Pay frequencies
    - GL mappings
    - Other code tables
    
    This gatherer:
    1. Identifies config tables (type='config' in _table_classifications)
    2. Generates SQL to query relevant config data
    3. Returns Truth objects with full provenance
    
    The key difference from RealityGatherer:
    - Reality = transactional/employee data (payroll runs, employee records)
    - Configuration = setup/code tables (how the system is configured)
    """
    
    truth_type = TruthType.CONFIGURATION
    
    # Config table indicators (tables that represent configuration, not data)
    CONFIG_INDICATORS = [
        'code', 'codes', 'mapping', 'mappings', 'setup', 'config',
        'type', 'types', 'category', 'categories', 'class', 'classes',
        'plan', 'plans', 'rate', 'rates', 'rule', 'rules',
        'earnings', 'deduction', 'deductions', 'tax', 'benefit',
        'gl_', 'acct_', 'account_', 'pay_freq', 'frequency',
    ]
    
    def __init__(self, project_name: str, project_id: str = None,
                 structured_handler=None, schema: Dict = None,
                 table_classifications: Dict = None):
        """
        Initialize Configuration gatherer.
        
        Args:
            project_name: Project code
            project_id: Project UUID
            structured_handler: DuckDB handler
            schema: Schema metadata (tables, columns)
            table_classifications: Dict of table_name -> classification info
        """
        super().__init__(project_name, project_id, structured_handler)
        self.schema = schema or {}
        self.table_classifications = table_classifications or {}
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Configuration truths for the question.
        
        Args:
            question: User's question
            context: Analysis context
            
        Returns:
            List of Truth objects from config tables
        """
        self.log_gather_start(question)
        
        if not self.handler or not self.schema:
            logger.debug("[GATHER-CONFIG] No handler or schema available")
            return []
        
        truths = []
        
        try:
            # Find relevant config tables
            config_tables = self._find_config_tables(question, context)
            
            if not config_tables:
                logger.debug("[GATHER-CONFIG] No relevant config tables found")
                return []
            
            # Query each relevant config table
            for table_info in config_tables[:3]:  # Limit to top 3 most relevant
                table_name = table_info.get('table_name')
                if not table_name:
                    continue
                
                truth = self._query_config_table(table_name, table_info, question)
                if truth:
                    truths.append(truth)
                    
        except Exception as e:
            logger.error(f"[GATHER-CONFIG] Error: {e}")
        
        self.log_gather_result(truths)
        return truths
    
    def _find_config_tables(self, question: str, context: Dict) -> List[Dict]:
        """Find config tables relevant to the question."""
        config_tables = []
        q_lower = question.lower()
        
        tables = self.schema.get('tables', [])
        
        for table in tables:
            table_name = table.get('table_name', '').lower()
            display_name = table.get('display_name', '').lower()
            
            # Check if it's classified as config
            # Handle both TableClassification objects and dicts
            classification = self.table_classifications.get(table_name)
            
            if classification is None:
                is_config = False
                domain = ''
            elif hasattr(classification, 'table_type'):
                # It's a TableClassification object
                is_config = str(getattr(classification, 'table_type', '')).lower() == 'config'
                domain = str(getattr(classification, 'domain', '')).lower()
            else:
                # It's a dict
                is_config = classification.get('table_type') == 'config'
                domain = classification.get('domain', '')
            
            # Also check table name for config indicators
            has_config_indicator = any(ind in table_name for ind in self.CONFIG_INDICATORS)
            
            if is_config or has_config_indicator:
                # Score relevance to question
                score = 0
                
                # Name match
                for word in q_lower.split():
                    if len(word) > 3:
                        if word in table_name:
                            score += 100
                        if word in display_name:
                            score += 80
                
                # Domain match
                if domain and domain in q_lower:
                    score += 50
                
                # Column match
                for col in table.get('columns', []):
                    col_name = col.get('name', '').lower() if isinstance(col, dict) else col.lower()
                    for word in q_lower.split():
                        if len(word) > 3 and word in col_name:
                            score += 20
                
                if score > 0 or is_config:
                    config_tables.append({
                        'table_name': table.get('table_name'),
                        'display_name': table.get('display_name'),
                        'score': score,
                        'classification': classification,
                        'row_count': table.get('row_count', 0)
                    })
        
        # Sort by score
        config_tables.sort(key=lambda x: x['score'], reverse=True)
        
        logger.debug(f"[GATHER-CONFIG] Found {len(config_tables)} config tables, "
                    f"top: {[t['table_name'] for t in config_tables[:3]]}")
        
        return config_tables
    
    def _query_config_table(self, table_name: str, table_info: Dict, 
                           question: str) -> Optional[Truth]:
        """Query a config table and return as Truth."""
        try:
            # Simple query - get all rows (config tables are usually small)
            row_count = table_info.get('row_count', 0)
            limit = min(100, max(50, row_count)) if row_count > 0 else 100
            
            sql = f'SELECT * FROM "{table_name}" LIMIT {limit}'
            rows = self.handler.query(sql)
            
            if not rows:
                return None
            
            columns = list(rows[0].keys()) if rows else []
            display_name = table_info.get('display_name') or table_name
            
            # Get domain from classification (handle both object and dict)
            classification = table_info.get('classification')
            if classification is None:
                domain = None
            elif hasattr(classification, 'domain'):
                domain = str(getattr(classification, 'domain', ''))
            else:
                domain = classification.get('domain') if isinstance(classification, dict) else None
            
            logger.debug(f"[GATHER-CONFIG] Queried {table_name}: {len(rows)} rows")
            
            return self.create_truth(
                source_name=display_name,
                content={
                    'sql': sql,
                    'columns': columns,
                    'rows': rows,
                    'total': len(rows),
                    'table': table_name,
                    'display_name': display_name,
                    'is_config_table': True,
                    'classification': classification
                },
                location=f"Config table: {display_name}",
                confidence=0.90,
                row_count=len(rows),
                column_count=len(columns),
                domain=domain
            )
            
        except Exception as e:
            logger.error(f"[GATHER-CONFIG] Error querying {table_name}: {e}")
            return None
