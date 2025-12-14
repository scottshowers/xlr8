"""
Query Intent Classifier - Advanced RAG Feature
===============================================

Classifies queries into intents for specialized handling

Intents:
- COUNT: "How many X?" → Aggregation handler
- LOOKUP: "What is X?" → Precise search (n=10)
- LIST: "Show all X" → Comprehensive retrieval (n=100)
- COMPARE: "X vs Y" → Multi-query comparison
- ANALYZE: "Analyze X" → Deep retrieval + reasoning

Author: XLR8 Team
"""

import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies query intent for optimal routing"""
    
    def __init__(self):
        # Intent patterns
        self.patterns = {
            'COUNT': [
                r'\bhow many\b',
                r'\bcount\b',
                r'\bnumber of\b',
                r'\btotal number\b',
            ],
            
            'LOOKUP': [
                r'\bwhat is\b',
                r'\bwhat are\b',
                r'\bdefine\b',
                r'\bexplain\b',
                r'\btell me about\b',
                r'\bshow me\s+(?:the|this)\b',  # "show me the earning code"
            ],
            
            'LIST': [
                r'\blist all\b',
                r'\bshow all\b',
                r'\bget all\b',
                r'\ball\b.*\bcodes?\b',
                r'\bevery\b',
                r'\bcomplete list\b',
            ],
            
            'COMPARE': [
                r'\bvs\b',
                r'\bversus\b',
                r'\bcompare\b',
                r'\bdifference between\b',
                r'\bbetter\b',
                r'\bmore\b.*\bthan\b',
            ],
            
            'ANALYZE': [
                r'\banalyze\b',
                r'\banalysis\b',
                r'\bevaluate\b',
                r'\bassess\b',
                r'\breview\b',
                r'\bsummarize\b',
            ],
        }
    
    def classify(self, query: str) -> Dict[str, Any]:
        """
        Classify query intent
        
        Returns:
            {
                'intent': str,
                'confidence': float,
                'recommended_n': int,
                'strategy': str
            }
        """
        query_lower = query.lower()
        
        # Check each intent pattern
        scores = {intent: 0 for intent in self.patterns.keys()}
        
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] += 1
        
        # Determine primary intent
        if max(scores.values()) == 0:
            # Default intent
            intent = 'GENERAL'
            confidence = 0.5
        else:
            intent = max(scores, key=scores.get)
            confidence = min(1.0, scores[intent] * 0.3)
        
        # Configure strategy based on intent
        config = self._get_intent_config(intent)
        
        logger.info(f"[INTENT] Classified as {intent} (confidence: {confidence:.1%})")
        
        return {
            'intent': intent,
            'confidence': confidence,
            **config
        }
    
    def _get_intent_config(self, intent: str) -> Dict[str, Any]:
        """Get retrieval configuration for intent"""
        
        configs = {
            'COUNT': {
                'recommended_n': 200,  # Get many chunks for accurate counting
                'strategy': 'exhaustive',
                'rerank': False
            },
            
            'LOOKUP': {
                'recommended_n': 10,  # Just need precise match
                'strategy': 'precise',
                'rerank': True
            },
            
            'LIST': {
                'recommended_n': 100,  # Comprehensive retrieval
                'strategy': 'comprehensive',
                'rerank': False
            },
            
            'COMPARE': {
                'recommended_n': 50,  # Balanced retrieval
                'strategy': 'multi-query',
                'rerank': True
            },
            
            'ANALYZE': {
                'recommended_n': 75,  # Deep retrieval
                'strategy': 'deep',
                'rerank': True
            },
            
            'GENERAL': {
                'recommended_n': 50,  # Default
                'strategy': 'standard',
                'rerank': False
            }
        }
        
        return configs.get(intent, configs['GENERAL'])


# Integration function
def classify_and_configure(query: str) -> Dict[str, Any]:
    """
    Classify query and return optimal configuration
    
    Returns:
        {
            'intent': str,
            'n_results': int,
            'use_aggregation': bool,
            'use_decomposition': bool,
            'rerank': bool
        }
    """
    classifier = IntentClassifier()
    result = classifier.classify(query)
    
    # Map to configuration
    config = {
        'intent': result['intent'],
        'n_results': result['recommended_n'],
        'use_aggregation': result['intent'] == 'COUNT',
        'use_decomposition': result['intent'] in ['COMPARE', 'LIST'],
        'rerank': result.get('rerank', False),
        'strategy': result.get('strategy', 'standard')
    }
    
    return config
