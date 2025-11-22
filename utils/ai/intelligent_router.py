"""
Intelligent Router for XLR8 Chat System

This module orchestrates the entire query processing flow:
1. PII Detection & Anonymization
2. Complexity Analysis & Model Selection
3. ChromaDB Context Retrieval
4. LLM Routing (Local vs Claude API)
5. Response Synthesis & De-anonymization

Author: HCMPACT
Version: 1.0.1 - Fixed ChromaDB search call
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

# Import our utility modules
from utils.ai.pii_handler import PIIHandler
from utils.ai.complexity_analyzer import ComplexityAnalyzer
from utils.ai.model_checker import ModelChecker

logger = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    """Decision made by the intelligent router"""
    use_local_llm: bool
    model_name: str
    reason: str
    has_pii: bool
    complexity: str
    chromadb_context: Optional[List[Dict]] = None
    anonymized_query: Optional[str] = None
    pii_map: Optional[Dict] = None


class IntelligentRouter:
    """
    Orchestrates query routing through the intelligent chat system.
    
    Decision Flow:
    1. Check for PII → If found, anonymize and force local LLM
    2. Check complexity → Simple: Mistral, Complex: DeepSeek
    3. Check ChromaDB → If HCMPACT docs exist, enhance with context
    4. If no PII and no ChromaDB → Route to Claude API for general knowledge
    """
    
    def __init__(self, 
                 ollama_endpoint: str,
                 ollama_auth: Optional[Tuple[str, str]] = None,
                 claude_api_key: Optional[str] = None,
                 chromadb_handler = None):
        """
        Initialize the intelligent router.
        
        Args:
            ollama_endpoint: URL for Ollama server (e.g., http://178.156.190.64:11435)
            ollama_auth: Optional tuple of (username, password) for Ollama
            claude_api_key: Optional API key for Claude
            chromadb_handler: Optional ChromaDB handler for context retrieval
        """
        self.ollama_endpoint = ollama_endpoint
        self.ollama_auth = ollama_auth
        self.claude_api_key = claude_api_key
        self.chromadb_handler = chromadb_handler
        
        # Initialize components
        self.pii_handler = PIIHandler()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.model_checker = ModelChecker(ollama_endpoint, ollama_auth)
        
        # Cache available models
        self.available_models = self._check_available_models()
        
        logger.info(f"Intelligent Router initialized with models: {self.available_models}")
    
    def _check_available_models(self) -> List[str]:
        """Check which models are available on Ollama server"""
        try:
            models = self.model_checker.list_models()
            return models if models else []
        except Exception as e:
            logger.warning(f"Could not check available models: {e}")
            return []
    
    def make_routing_decision(
        self, 
        query: str, 
        num_chromadb_sources: int = 50,
        project_id: Optional[str] = None,
        functional_areas: Optional[List[str]] = None  # ← ADDED FOR FUNCTIONAL AREA FILTERING
    ) -> RouterDecision:
        """
        Make an intelligent routing decision for the given query.
        
        Args:
            query: User's query text
            num_chromadb_sources: Number of ChromaDB sources to retrieve
            project_id: Optional project ID to filter ChromaDB results
            functional_areas: Optional list of functional areas to filter results
            
        Returns:
            RouterDecision object with routing information
        """
        
        # STEP 1: PII Detection
        logger.debug("Step 1: Checking for PII")
        has_pii = self.pii_handler.has_pii(query)
        
        if has_pii:
            # Anonymize query and force local LLM
            anonymized_query, pii_map = self.pii_handler.anonymize(query)
            logger.info("PII detected - routing to local LLM only")
            
            # Check complexity to select local model
            complexity_result = self.complexity_analyzer.analyze(query)
            model_name = self._select_local_model(complexity_result['complexity'])
            
            return RouterDecision(
                use_local_llm=True,
                model_name=model_name,
                reason=f"PII detected - must use local LLM. Complexity: {complexity_result['complexity']}",
                has_pii=True,
                complexity=complexity_result['complexity'],
                anonymized_query=anonymized_query,
                pii_map=pii_map
            )
        
        # STEP 2: Check ChromaDB for HCMPACT context
        logger.debug("Step 2: Checking ChromaDB for context")
        chromadb_context = self._get_chromadb_context(
            query, 
            num_chromadb_sources, 
            project_id,
            functional_areas
        )
        
        if chromadb_context and len(chromadb_context) > 0:
            # HCMPACT-specific knowledge exists
            num_results = len(chromadb_context)
            logger.info(f"Found {num_results} ChromaDB sources")
            
            # SMART HYBRID with RERANKING:
            # Reranker caps results at 20 for quality
            # 0-20 sources + no PII → Claude API (fast, high quality)
            # 20+ sources (rare after reranking) OR PII → Local LLM
            
            if not has_pii and num_results <= 40 and self.claude_api_key:
                # Small context + no PII → Use Claude API
                logger.info(f"✅ SMART HYBRID: {num_results} sources (≤40) - routing to Claude API")
                complexity_result = self.complexity_analyzer.analyze(query, num_results)
                
                return RouterDecision(
                    use_local_llm=False,
                    model_name="claude-sonnet-4-20250514",
                    reason=f"HCMPACT knowledge ({num_results} sources ≤40) - Claude API can handle efficiently. {complexity_result['reason']}",
                    has_pii=False,
                    complexity=complexity_result['complexity'],
                    chromadb_context=chromadb_context
                )
            else:
                # Large context OR PII → Use local LLM
                reason_parts = []
                if has_pii:
                    reason_parts.append("PII detected")
                if num_results > 40:
                    reason_parts.append(f"{num_results} sources (>40)")
                reason_suffix = " + ".join(reason_parts) if reason_parts else "HCMPACT data"
                
                logger.info(f"✅ Using LOCAL LLM: {reason_suffix} - your proprietary data stays secure")
                
                complexity_result = self.complexity_analyzer.analyze(query, num_results)
                
                # CRITICAL: For large context (>40 sources), ALWAYS use Mistral (fast)
                # DeepSeek is too slow and times out with large context
                if num_results > 40:
                    model_name = self._select_local_model('simple')  # Force Mistral
                    logger.info(f"Large context ({num_results} sources) - using Mistral for speed")
                else:
                    model_name = self._select_local_model(complexity_result['complexity'])
                
                logger.info(f"Using LOCAL LLM ({model_name}) with {num_results} HCMPACT sources")
                
                return RouterDecision(
                    use_local_llm=True,
                    model_name=model_name,
                    reason=f"{reason_suffix} - using local LLM for proprietary data. {complexity_result['reason']}",
                    has_pii=has_pii,
                    complexity=complexity_result['complexity'],
                    chromadb_context=chromadb_context
                )
        
        # STEP 3: Analyze complexity for routing decision
        logger.debug("Step 3: Analyzing query complexity")
        complexity_result = self.complexity_analyzer.analyze(query)
        
        # STEP 4: Routing decision
        # If complex question and no HCMPACT context, could use DeepSeek or Claude
        # If simple/medium and no HCMPACT context, prefer Claude API for speed
        
        if complexity_result['complexity'] == 'complex':
            # Complex questions get DeepSeek's reasoning capability
            model_name = self._select_local_model('complex')
            logger.info("Complex query - routing to DeepSeek-r1")
            
            return RouterDecision(
                use_local_llm=True,
                model_name=model_name,
                reason=f"Complex query requires deep reasoning. {complexity_result['reason']}",
                has_pii=False,
                complexity=complexity_result['complexity']
            )
        else:
            # Simple/medium questions without HCMPACT context → Claude API
            if self.claude_api_key:
                logger.info(f"{complexity_result['complexity'].capitalize()} query - routing to Claude API")
                return RouterDecision(
                    use_local_llm=False,
                    model_name="claude-sonnet-4-20250514",
                    reason=f"General knowledge question - Claude API optimal. {complexity_result['reason']}",
                    has_pii=False,
                    complexity=complexity_result['complexity']
                )
            else:
                # No Claude API key - use local LLM
                model_name = self._select_local_model(complexity_result['complexity'])
                logger.info("No Claude API key - using local LLM")
                
                return RouterDecision(
                    use_local_llm=True,
                    model_name=model_name,
                    reason=f"Claude API not available - using local LLM. {complexity_result['reason']}",
                    has_pii=False,
                    complexity=complexity_result['complexity']
                )
    
    def _select_local_model(self, complexity: str) -> str:
        """
        Select the appropriate local model based on complexity.
        
        Args:
            complexity: 'simple', 'medium', or 'complex'
            
        Returns:
            Model name to use
        """
        # Preference: DeepSeek for complex, Mistral for simple/medium
        if complexity == 'complex':
            preferred = ["deepseek-r1:7b", "deepseek-r1:latest", "mixtral:8x7b"]
        else:
            preferred = ["mistral:7b", "mistral:latest", "mixtral:8x7b"]
        
        # Find first available model from preferences
        for model in preferred:
            if model in self.available_models:
                return model
        
        # Fallback: use first available model or default
        if self.available_models:
            return self.available_models[0]
        
        # Last resort: return expected model name even if not verified
        return "mistral:7b" if complexity != 'complex' else "deepseek-r1:7b"
    
    def _get_chromadb_context(
        self, 
        query: str, 
        num_sources: int,
        project_id: Optional[str] = None,
        functional_areas: Optional[List[str]] = None  # ← ADDED FOR FUNCTIONAL AREA FILTERING
    ) -> Optional[List[Dict]]:
        """
        Retrieve relevant context from ChromaDB if available.
        SEARCHES BOTH COLLECTIONS (hcmpact_knowledge AND hcmpact_docs)
        
        Args:
            query: User's query
            num_sources: Number of sources to retrieve
            project_id: Optional project ID to filter results
            functional_areas: Optional list of functional areas to filter results
            
        Returns:
            List of context documents or None
        """
        if not self.chromadb_handler:
            return None
        
        all_results = []
        
        # Search BOTH collections
        collections_to_search = ["hcmpact_knowledge", "hcmpact_docs"]
        
        for collection_name in collections_to_search:
            try:
                logger.info(f"Searching ChromaDB collection: '{collection_name}'")
                
                # Log project filtering status
                if project_id:
                    logger.info(f"[PROJECT] Filtering search by project_id: {project_id}")
                else:
                    logger.info("[PROJECT] Searching all projects (no filter)")
                
                # Log functional area filtering status
                if functional_areas:
                    logger.info(f"[FUNCTIONAL AREA] Filtering by: {', '.join(functional_areas)}")
                else:
                    logger.info("[FUNCTIONAL AREA] No filter - searching all areas")
                
                results = self.chromadb_handler.search(
                    collection_name=collection_name,
                    query=query,
                    n_results=num_sources,
                    project_id=project_id,
                    functional_areas=functional_areas  # ← ADDED FOR FUNCTIONAL AREA FILTERING
                )
                
                if results and len(results) > 0:
                    logger.info(f"Found {len(results)} results from '{collection_name}'")
                    all_results.extend(results)
                else:
                    logger.info(f"No results found in '{collection_name}'")
                    
            except Exception as e:
                logger.warning(f"Search failed for '{collection_name}': {e}")
                continue
        
        # Combine and sort by relevance (distance)
        if all_results:
            # Sort by distance (lower is better)
            all_results.sort(key=lambda x: x.get('distance', 999))
            
            # RERANKING: If we have many results, rerank for quality
            if len(all_results) > 20:
                logger.info(f"Reranking {len(all_results)} results for better relevance")
                from utils.reranker import rerank_results
                
                # Calculate target: keep more results if requested, but max 20 for LLM
                target_count = min(20, num_sources)
                
                reranked_results = rerank_results(
                    query=query,
                    results=all_results,
                    top_k=target_count
                )
                
                logger.info(f"Reranked: Keeping top {len(reranked_results)} most relevant results")
                top_results = reranked_results
            else:
                # Not enough results to benefit from reranking
                top_results = all_results[:num_sources]
            
            logger.info(f"Final: {len(top_results)} results for LLM")
            if project_id:
                logger.info(f"[PROJECT] Results filtered to project: {project_id}")
            
            return top_results
        
        logger.info("No results found in any collection")
        return None
    
    def get_decision_explanation(self, decision: RouterDecision) -> str:
        """
        Generate a user-friendly explanation of the routing decision.
        
        Args:
            decision: RouterDecision object
            
        Returns:
            Human-readable explanation
        """
        parts = []
        
        # PII status
        if decision.has_pii:
            parts.append("🔒 PII detected - using secure local processing")
        
        # Model selection
        if decision.use_local_llm:
            model_display = decision.model_name.replace(":7b", "").replace(":latest", "")
            parts.append(f"🤖 Using {model_display}")
        else:
            parts.append("🤖 Using Claude API")
        
        # Complexity
        complexity_emoji = {
            'simple': '⚡',
            'medium': '🎯',
            'complex': '🧠'
        }
        emoji = complexity_emoji.get(decision.complexity, '')
        parts.append(f"{emoji} {decision.complexity.capitalize()} query")
        
        # Context
        if decision.chromadb_context:
            parts.append(f"📚 Enhanced with {len(decision.chromadb_context)} HCMPACT sources")
        
        return " | ".join(parts)
    
    def process_response(self, response: str, decision: RouterDecision) -> str:
        """
        Post-process the LLM response (e.g., de-anonymize PII).
        
        Args:
            response: Raw LLM response
            decision: RouterDecision that was used
            
        Returns:
            Processed response
        """
        if decision.has_pii and decision.pii_map:
            # De-anonymize the response
            return self.pii_handler.deanonymize(response, decision.pii_map)
        
        return response


# Convenience function for easy usage
def route_query(query: str,
                ollama_endpoint: str,
                ollama_auth: Optional[Tuple[str, str]] = None,
                claude_api_key: Optional[str] = None,
                chromadb_handler = None) -> RouterDecision:
    """
    Convenience function to route a single query.
    
    Args:
        query: User's query
        ollama_endpoint: Ollama server URL
        ollama_auth: Optional (username, password) tuple
        claude_api_key: Optional Claude API key
        chromadb_handler: Optional ChromaDB handler
        
    Returns:
        RouterDecision object
    """
    router = IntelligentRouter(
        ollama_endpoint=ollama_endpoint,
        ollama_auth=ollama_auth,
        claude_api_key=claude_api_key,
        chromadb_handler=chromadb_handler
    )
    
    return router.make_routing_decision(query)
