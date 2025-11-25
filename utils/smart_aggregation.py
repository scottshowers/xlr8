"""
Smart Aggregation Handler - Advanced RAG Feature
================================================

Handles aggregation queries (count, sum, total, how many) by retrieving
ALL relevant chunks and computing precise answers.

Author: XLR8 Team
"""

from typing import List, Dict, Any, Optional, Set
import re
import logging

logger = logging.getLogger(__name__)


class AggregationDetector:
    """Detects if query needs aggregation (count, sum, total)"""
    
    def __init__(self):
        self.count_patterns = [
            r'\bhow many\b',
            r'\bcount\b',
            r'\bnumber of\b',
            r'\btotal number\b',
            r'\bhow much\b',
            r'\blist all\b',
            r'\bshow all\b',
            r'\ball\b.*\b(?:are there|exist)',
        ]
        
        self.sum_patterns = [
            r'\btotal\b',
            r'\bsum\b',
            r'\baggregate\b',
            r'\bcombined\b',
        ]
    
    def needs_aggregation(self, query: str) -> Dict[str, Any]:
        """
        Detect if query needs aggregation
        
        Returns:
            Dict with: {
                'needs_agg': bool,
                'agg_type': 'count' | 'sum' | None,
                'entity': str (what to count/sum)
            }
        """
        query_lower = query.lower()
        
        # Check for count patterns
        for pattern in self.count_patterns:
            if re.search(pattern, query_lower):
                # Extract entity (what to count)
                entity = self._extract_entity(query, pattern)
                return {
                    'needs_agg': True,
                    'agg_type': 'count',
                    'entity': entity
                }
        
        # Check for sum patterns
        for pattern in self.sum_patterns:
            if re.search(pattern, query_lower):
                entity = self._extract_entity(query, pattern)
                return {
                    'needs_agg': True,
                    'agg_type': 'sum',
                    'entity': entity
                }
        
        return {'needs_agg': False, 'agg_type': None, 'entity': None}
    
    def _extract_entity(self, query: str, pattern: str) -> str:
        """Extract the entity being counted/summed"""
        query_lower = query.lower()
        
        # Common entities
        entities = {
            'earning': ['earnings', 'earning codes', 'earnings codes'],
            'deduction': ['deductions', 'deduction codes'],
            'benefit': ['benefits', 'benefit plans'],
            'pay group': ['pay groups', 'paygroups'],
            'location': ['locations', 'sites'],
            'employee': ['employees', 'workers', 'people'],
            'gl account': ['gl accounts', 'gl rules', 'general ledger'],
        }
        
        for key, variations in entities.items():
            for variation in variations:
                if variation in query_lower:
                    return key
        
        # Fallback: extract noun after pattern
        match = re.search(pattern + r'\s+(\w+)', query_lower)
        if match:
            return match.group(1)
        
        return 'items'


class SmartAggregator:
    """
    Performs smart aggregation by retrieving ALL relevant chunks
    and computing precise counts/sums
    """
    
    def __init__(self, rag_handler):
        self.rag_handler = rag_handler
        self.detector = AggregationDetector()
    
    def process_aggregation(
        self,
        collection,
        query: str,
        where_filter: Optional[Dict] = None,
        max_chunks: int = 200
    ) -> Dict[str, Any]:
        """
        Process aggregation query
        
        Args:
            collection: ChromaDB collection
            query: User query
            where_filter: Optional filter
            max_chunks: Max chunks to retrieve for aggregation
        
        Returns:
            Dict with aggregation results
        """
        # Detect aggregation need
        agg_info = self.detector.needs_aggregation(query)
        
        if not agg_info['needs_agg']:
            return {'needs_agg': False}
        
        logger.info(f"[AGGREGATION] Type: {agg_info['agg_type']}, Entity: {agg_info['entity']}")
        
        # Get embedding
        query_embedding = self.rag_handler.get_embedding(query)
        if not query_embedding:
            return {'needs_agg': False, 'error': 'Failed to create embedding'}
        
        # Retrieve MORE chunks for accurate counting
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max_chunks,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results['documents'][0]:
            return {
                'needs_agg': True,
                'agg_type': agg_info['agg_type'],
                'count': 0,
                'items': []
            }
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        logger.info(f"[AGGREGATION] Retrieved {len(documents)} chunks for counting")
        
        # Extract unique items based on aggregation type
        if agg_info['agg_type'] == 'count':
            items = self._extract_items(documents, metadatas, agg_info['entity'])
            
            return {
                'needs_agg': True,
                'agg_type': 'count',
                'count': len(items),
                'items': list(items)[:50],  # First 50 for display
                'total_chunks': len(documents),
                'entity': agg_info['entity']
            }
        
        # Add sum logic if needed in future
        
        return {'needs_agg': False}
    
    def _extract_items(
        self, 
        documents: List[str], 
        metadatas: List[Dict],
        entity: str
    ) -> Set[str]:
        """
        Extract unique items from documents
        
        For earnings/deductions: Extract codes
        For locations: Extract location names
        etc.
        """
        items = set()
        
        # Pattern matching based on entity type
        if entity in ['earning', 'deduction', 'benefit']:
            # Look for codes (3-6 uppercase letters/numbers)
            pattern = r'\b([A-Z0-9]{2,10})\b'
            
            for doc in documents:
                # Extract codes from document
                matches = re.findall(pattern, doc)
                for match in matches:
                    # Filter out common words
                    if match not in ['USA', 'CODE', 'TYPE', 'NAME', 'TOTAL', 'AMOUNT']:
                        items.add(match)
        
        elif entity in ['pay group', 'location', 'employee']:
            # Look for names (extract from structured data)
            # This is more complex, would need better parsing
            pattern = r'(?:Code|Name):\s*([A-Za-z0-9\s\-]+)'
            
            for doc in documents:
                matches = re.findall(pattern, doc)
                for match in matches:
                    items.add(match.strip())
        
        logger.info(f"[AGGREGATION] Extracted {len(items)} unique {entity}s")
        
        return items
    
    def format_response(self, agg_result: Dict, query: str) -> str:
        """
        Format aggregation result as natural language
        
        Args:
            agg_result: Aggregation result dict
            query: Original query
        
        Returns:
            Formatted response string
        """
        if not agg_result.get('needs_agg'):
            return None
        
        count = agg_result['count']
        entity = agg_result['entity']
        items = agg_result.get('items', [])
        
        # Build response
        if agg_result['agg_type'] == 'count':
            response = f"There are **{count} {entity}s** total"
            
            if items and len(items) <= 20:
                # List them if not too many
                response += ":\n\n"
                for item in sorted(items):
                    response += f"- {item}\n"
            elif items:
                # Show sample
                response += f". Here are some examples:\n\n"
                for item in sorted(items)[:10]:
                    response += f"- {item}\n"
                response += f"\n... and {count - 10} more."
        
        return response


# Integration function
def handle_aggregation(
    rag_handler,
    collection,
    query: str,
    where_filter: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Check if query needs aggregation and handle it
    
    Returns:
        Aggregation result if needed, None otherwise
    """
    aggregator = SmartAggregator(rag_handler)
    result = aggregator.process_aggregation(collection, query, where_filter)
    
    if result.get('needs_agg'):
        # Format natural language response
        formatted = aggregator.format_response(result, query)
        result['formatted_response'] = formatted
        return result
    
    return None
