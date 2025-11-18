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
    
    def make_routing_decision(self, query: str, num_chromadb_sources: int = 5) -> RouterDecision:
        """
        Make an intelligent routing decision for the given query.
        
        Args:
            query: User's query text
            num_chromadb_sources: Number of ChromaDB sources to retrieve
            
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
        chromadb_context = self._get_chromadb_context(query, num_chromadb_sources)
        
        if chromadb_context and len(chromadb_context) > 0:
            # HCMPACT-specific knowledge exists
            logger.info(f"Found {len(chromadb_context)} ChromaDB sources")
            
            complexity_result = self.complexity_analyzer.analyze(query, len(chromadb_context))
            
            # HYBRID MODE: If Claude API available, use it to synthesize with local context
            if self.claude_api_key:
                logger.info(f"Using HYBRID mode: Claude synthesizes with {len(chromadb_context)} local sources")
                return RouterDecision(
                    use_local_llm=False,  # Claude API will synthesize
                    model_name="claude-sonnet-4-20250514",
                    reason=f"Hybrid Mode: Claude synthesizing with {len(chromadb_context)} HCMPACT sources. {complexity_result['reason']}",
                    has_pii=False,
                    complexity=complexity_result['complexity'],
                    chromadb_context=chromadb_context
                )
            else:
                # No Claude API - use local LLM
                model_name = self._select_local_model(complexity_result['complexity'])
                logger.info(f"No Claude API - using local LLM with {len(chromadb_context)} sources")
                
                return RouterDecision(
                    use_local_llm=True,
                    model_name=model_name,
                    reason=f"HCMPACT knowledge available ({len(chromadb_context)} sources). {complexity_result['reason']}",
                    has_pii=False,
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
    
    def _get_chromadb_context(self, query: str, num_sources: int) -> Optional[List[Dict]]:
        """
        Retrieve relevant context from ChromaDB if available.
        
        Args:
            query: User's query
            num_sources: Number of sources to retrieve
            
        Returns:
            List of context documents or None
        """
        if not self.chromadb_handler:
            return None
        
        try:
            # FIXED: Added collection_name parameter
            results = self.chromadb_handler.search(
                query=query,
                collection_name="default",  # ← FIX: Added required parameter
                n_results=num_sources
            )
            
            if results and len(results) > 0:
                return results
            
            return None
            
        except Exception as e:
            logger.warning(f"ChromaDB context retrieval failed: {e}")
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
