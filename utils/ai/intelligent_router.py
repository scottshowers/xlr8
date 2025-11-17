"""
Intelligent Router - DIAGNOSTIC VERSION with timing
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging
import time

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
    """Intelligent router with diagnostic timing"""
    
    def __init__(self, 
                 ollama_endpoint: str,
                 ollama_auth: Optional[Tuple[str, str]] = None,
                 claude_api_key: Optional[str] = None,
                 chromadb_handler = None):
        self.ollama_endpoint = ollama_endpoint
        self.ollama_auth = ollama_auth
        self.claude_api_key = claude_api_key
        self.chromadb_handler = chromadb_handler
        
        self.pii_handler = PIIHandler()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.model_checker = ModelChecker(ollama_endpoint, ollama_auth)
        
        self.available_models = self._check_available_models()
        
        logger.info(f"Router initialized with models: {self.available_models}")
    
    def _check_available_models(self) -> List[str]:
        try:
            models = self.model_checker.list_models()
            return models if models else []
        except Exception as e:
            logger.warning(f"Could not check models: {e}")
            return []
    
    def make_routing_decision(self, query: str, num_chromadb_sources: int = 5) -> RouterDecision:
        """Make routing decision with timing diagnostics"""
        
        start_time = time.time()
        
        # STEP 1: PII Detection
        pii_start = time.time()
        has_pii = self.pii_handler.has_pii(query)
        pii_time = time.time() - pii_start
        print(f"[ROUTER] PII check: {pii_time:.3f}s")
        
        if has_pii:
            anonymized_query, pii_map = self.pii_handler.anonymize(query)
            complexity_result = self.complexity_analyzer.analyze(query)
            model_name = self._select_local_model(complexity_result['complexity'])
            
            return RouterDecision(
                use_local_llm=True,
                model_name=model_name,
                reason=f"PII detected - must use local LLM",
                has_pii=True,
                complexity=complexity_result['complexity'],
                anonymized_query=anonymized_query,
                pii_map=pii_map
            )
        
        # STEP 2: Check ChromaDB
        chromadb_start = time.time()
        chromadb_context = self._get_chromadb_context(query, num_chromadb_sources)
        chromadb_time = time.time() - chromadb_start
        print(f"[ROUTER] ChromaDB search: {chromadb_time:.3f}s, found {len(chromadb_context) if chromadb_context else 0} results")
        
        if chromadb_context and len(chromadb_context) > 0:
            complexity_result = self.complexity_analyzer.analyze(query, len(chromadb_context))
            model_name = self._select_local_model(complexity_result['complexity'])
            
            total_time = time.time() - start_time
            print(f"[ROUTER] Total routing time: {total_time:.3f}s")
            
            return RouterDecision(
                use_local_llm=True,
                model_name=model_name,
                reason=f"HCMPACT knowledge available ({len(chromadb_context)} sources)",
                has_pii=False,
                complexity=complexity_result['complexity'],
                chromadb_context=chromadb_context
            )
        
        # STEP 3: Complexity analysis
        complexity_result = self.complexity_analyzer.analyze(query)
        
        if complexity_result['complexity'] == 'complex':
            model_name = self._select_local_model('complex')
            return RouterDecision(
                use_local_llm=True,
                model_name=model_name,
                reason=f"Complex query requires deep reasoning",
                has_pii=False,
                complexity=complexity_result['complexity']
            )
        else:
            if self.claude_api_key:
                return RouterDecision(
                    use_local_llm=False,
                    model_name="claude-sonnet-4-20250514",
                    reason=f"General knowledge - Claude API optimal",
                    has_pii=False,
                    complexity=complexity_result['complexity']
                )
            else:
                model_name = self._select_local_model(complexity_result['complexity'])
                return RouterDecision(
                    use_local_llm=True,
                    model_name=model_name,
                    reason=f"Claude API not available - using local LLM",
                    has_pii=False,
                    complexity=complexity_result['complexity']
                )
    
    def _select_local_model(self, complexity: str) -> str:
        """Select local model based on complexity"""
        if complexity == 'complex':
            preferred = ["deepseek-r1:7b", "deepseek-r1:latest", "mixtral:8x7b"]
        else:
            preferred = ["mistral:7b", "mistral:latest", "mixtral:8x7b"]
        
        for model in preferred:
            if model in self.available_models:
                return model
        
        if self.available_models:
            return self.available_models[0]
        
        return "mistral:7b" if complexity != 'complex' else "deepseek-r1:7b"
    
    def _get_chromadb_context(self, query: str, num_sources: int) -> Optional[List[Dict]]:
        """Retrieve ChromaDB context with timing"""
        if not self.chromadb_handler:
            return None
        
        try:
            search_start = time.time()
            
            if hasattr(self.chromadb_handler, 'multi_strategy_search'):
                results_by_strategy = self.chromadb_handler.multi_strategy_search(
                    query=query,
                    n_results_per_strategy=num_sources
                )
                
                search_time = time.time() - search_start
                print(f"[ROUTER] Multi-strategy search: {search_time:.3f}s")
                
                # Merge results
                all_results = []
                seen_content = set()
                
                for strategy, results in results_by_strategy.items():
                    print(f"[ROUTER]   Strategy '{strategy}': {len(results)} results")
                    for result in results:
                        content = result.get('content', '')
                        if content and content not in seen_content:
                            seen_content.add(content)
                            all_results.append(result)
                
                if all_results and 'distance' in all_results[0]:
                    all_results.sort(key=lambda x: x.get('distance', 1.0))
                
                return all_results[:num_sources] if all_results else None
            else:
                results = self.chromadb_handler.search(
                    query=query,
                    n_results=num_sources
                )
                
                search_time = time.time() - search_start
                print(f"[ROUTER] Single search: {search_time:.3f}s")
                
                return results if results and len(results) > 0 else None
            
        except Exception as e:
            logger.warning(f"ChromaDB retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_decision_explanation(self, decision: RouterDecision) -> str:
        """Get user-friendly explanation"""
        parts = []
        
        if decision.has_pii:
            parts.append("PII detected - secure local processing")
        
        if decision.use_local_llm:
            model_display = decision.model_name.replace(":7b", "").replace(":latest", "")
            parts.append(f"Using {model_display}")
        else:
            parts.append("Using Claude API")
        
        parts.append(f"{decision.complexity.capitalize()} query")
        
        if decision.chromadb_context:
            parts.append(f"Enhanced with {len(decision.chromadb_context)} HCMPACT sources")
        
        return " | ".join(parts)
    
    def process_response(self, response: str, decision: RouterDecision) -> str:
        """Post-process response"""
        if decision.has_pii and decision.pii_map:
            return self.pii_handler.deanonymize(response, decision.pii_map)
        return response
