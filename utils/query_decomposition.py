"""
Query Decomposition System - Advanced RAG Feature
==================================================

Handles compound questions by splitting into sub-queries and retrieving
diverse results across multiple sheets/sections.

Example:
  Query: "Give me deduction groups and pay groups"
  → Sub-queries: ["deduction groups", "pay groups"]
  → Retrieve from each sheet separately
  → Merge results with diversity

Author: XLR8 Team
"""

from typing import List, Dict, Any, Set, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class QueryDecomposer:
    """
    Detects compound questions and decomposes them into sub-queries
    """
    
    def __init__(self):
        # Sheet/table names that commonly appear in queries
        self.known_sheets = [
            'earnings', 'deductions', 'deduction', 'pay groups', 'pay group',
            'benefits', 'benefit', 'gl rules', 'gl accounts', 'locations',
            'organizations', 'tax', 'banks', 'projects', 'pto', 'unions',
            'job codes', 'workers comp', 'salary grades', 'payscale',
            'establishments', 'company', 'master', 'configuration'
        ]
        
        # Compound indicators
        self.compound_indicators = [
            r'\band\b',           # "earnings and deductions"
            r'\bor\b',            # "earnings or deductions"
            r',',                 # "earnings, deductions, pay groups"
            r'\balso\b',          # "also show me"
            r'\bplus\b',          # "plus pay groups"
            r'\bas well as\b',    # "as well as"
        ]
        
    def is_compound_query(self, query: str) -> bool:
        """
        Detect if query asks about multiple topics
        
        Args:
            query: User query
            
        Returns:
            True if compound query detected
        """
        query_lower = query.lower()
        
        # Check for compound indicators
        for pattern in self.compound_indicators:
            if re.search(pattern, query_lower):
                # Make sure it's not just "and" in a phrase like "gross and net"
                # Look for multiple sheet names
                sheet_matches = sum(1 for sheet in self.known_sheets if sheet in query_lower)
                if sheet_matches >= 2:
                    return True
        
        return False
    
    def decompose_query(self, query: str) -> List[str]:
        """
        Split compound query into sub-queries
        
        Args:
            query: Compound query
            
        Returns:
            List of sub-queries
        """
        if not self.is_compound_query(query):
            return [query]  # Not compound, return as-is
        
        query_lower = query.lower()
        sub_queries = []
        
        # Extract sheet names mentioned
        mentioned_sheets = []
        for sheet in self.known_sheets:
            if sheet in query_lower:
                mentioned_sheets.append(sheet)
        
        if not mentioned_sheets:
            return [query]  # No recognizable sheets, return as-is
        
        # Build sub-queries for each sheet
        for sheet in mentioned_sheets:
            # Extract the action/question part
            # Examples:
            # "Give me deduction groups and pay groups" 
            #   → "Give me deduction groups", "Give me pay groups"
            # "How many earnings and deductions are there?"
            #   → "How many earnings are there?", "How many deductions are there?"
            
            # Simple approach: Replace all other sheet names with the current one
            sub_query = query
            for other_sheet in mentioned_sheets:
                if other_sheet != sheet:
                    # Remove other sheet references
                    sub_query = re.sub(
                        r'\b' + re.escape(other_sheet) + r'\b',
                        '',
                        sub_query,
                        flags=re.IGNORECASE
                    )
            
            # Clean up conjunctions
            sub_query = re.sub(r'\s+and\s+', ' ', sub_query, flags=re.IGNORECASE)
            sub_query = re.sub(r'\s+or\s+', ' ', sub_query, flags=re.IGNORECASE)
            sub_query = re.sub(r',\s*', ' ', sub_query)
            sub_query = re.sub(r'\s+', ' ', sub_query).strip()
            
            if sub_query and len(sub_query) > 3:
                sub_queries.append(sub_query)
        
        # Fallback: If decomposition failed, split by conjunctions
        if not sub_queries:
            sub_queries = re.split(r'\s+(?:and|or)\s+', query, flags=re.IGNORECASE)
        
        logger.info(f"[DECOMPOSE] Original: {query}")
        logger.info(f"[DECOMPOSE] Sub-queries: {sub_queries}")
        
        return sub_queries if sub_queries else [query]


class DiverseRetriever:
    """
    Retrieves results with diversity across multiple sheets/sections
    """
    
    def __init__(self, rag_handler):
        self.rag_handler = rag_handler
        self.decomposer = QueryDecomposer()
    
    def retrieve_diverse(
        self,
        collection_name: str,
        query: str,
        n_results: int = 50,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve with diversity for compound queries
        
        Args:
            collection_name: ChromaDB collection name
            query: User query (possibly compound)
            n_results: Total results to return
            project_id: Optional project filter
            
        Returns:
            Dict with diverse results
        """
        # Check if compound query
        if not self.decomposer.is_compound_query(query):
            # Not compound, use normal retrieval
            return self.rag_handler.search_documents(
                collection_name=collection_name,
                query=query,
                n_results=n_results,
                project_id=project_id
            )
        
        # Decompose into sub-queries
        sub_queries = self.decomposer.decompose_query(query)
        
        logger.info(f"[DIVERSE] Compound query detected, splitting into {len(sub_queries)} sub-queries")
        
        # Retrieve for each sub-query
        results_per_query = n_results // len(sub_queries)
        all_results = {
            'ids': [],
            'documents': [],
            'metadatas': [],
            'distances': []
        }
        
        seen_ids = set()
        
        for i, sub_query in enumerate(sub_queries):
            logger.info(f"[DIVERSE] Sub-query {i+1}: {sub_query}")
            
            # Search for this sub-query
            sub_results = self.rag_handler.search_documents(
                collection_name=collection_name,
                query=sub_query,
                n_results=results_per_query + 10,  # Get extra to account for deduplication
                project_id=project_id
            )
            
            # Add results, deduplicating by ID
            if sub_results and 'ids' in sub_results:
                for j in range(len(sub_results['ids'][0])):
                    doc_id = sub_results['ids'][0][j]
                    
                    # Skip duplicates
                    if doc_id in seen_ids:
                        continue
                    
                    seen_ids.add(doc_id)
                    
                    # Add to combined results
                    all_results['ids'].append(doc_id)
                    all_results['documents'].append(sub_results['documents'][0][j])
                    all_results['metadatas'].append(sub_results['metadatas'][0][j])
                    all_results['distances'].append(sub_results['distances'][0][j])
                    
                    # Stop if we have enough
                    if len(all_results['ids']) >= n_results:
                        break
            
            if len(all_results['ids']) >= n_results:
                break
        
        # Wrap in list format (ChromaDB format)
        result = {
            'ids': [all_results['ids']],
            'documents': [all_results['documents']],
            'metadatas': [all_results['metadatas']],
            'distances': [all_results['distances']]
        }
        
        logger.info(f"[DIVERSE] Retrieved {len(all_results['ids'])} diverse results from {len(sub_queries)} sub-queries")
        
        # Log sheet diversity
        sheets_found = set()
        for meta in all_results['metadatas']:
            if 'parent_section' in meta:
                sheets_found.add(meta['parent_section'])
        logger.info(f"[DIVERSE] Sheets covered: {', '.join(sorted(sheets_found))}")
        
        return result


# Integration function for chat handler
def search_with_diversity(
    rag_handler,
    collection_name: str,
    query: str,
    n_results: int = 50,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point: Search with automatic diversity for compound queries
    
    Use this instead of rag_handler.search_documents() for better results
    on compound questions.
    
    Args:
        rag_handler: RAGHandler instance
        collection_name: ChromaDB collection
        query: User query
        n_results: Number of results
        project_id: Optional project filter
        
    Returns:
        Search results with diversity
    """
    retriever = DiverseRetriever(rag_handler)
    return retriever.retrieve_diverse(
        collection_name=collection_name,
        query=query,
        n_results=n_results,
        project_id=project_id
    )
