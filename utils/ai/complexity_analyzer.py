"""
Complexity Analyzer for XLR8 Chat System

Analyzes query complexity to determine optimal model selection:
- Simple queries → Mistral:7b (fast)
- Medium queries → Mistral:7b (fast enough)
- Complex queries → DeepSeek-r1:7b (reasoning capability)

Analysis based on:
- Word count
- Technical terminology
- Question complexity indicators
- Comparative/analytical language

Author: HCMPACT
Version: 1.0
"""

import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ComplexityAnalyzer:
    """
    Analyzes query complexity to recommend appropriate LLM model.
    
    Complexity Levels:
    - Simple: Quick lookups, definitions, basic questions
    - Medium: Explanations, comparisons, multi-part questions
    - Complex: Deep analysis, strategic planning, reasoning tasks
    """
    
    def __init__(self):
        """Initialize complexity analysis patterns"""
        
        # Indicators of complex queries
        self.complex_indicators = [
            r'\b(?:analyze|analysis|compare|contrast|evaluate|assess)\b',
            r'\b(?:strategy|strategic|approach|methodology)\b',
            r'\b(?:pros and cons|advantages and disadvantages|trade-?offs)\b',
            r'\b(?:why|how come|explain why|what if)\b',
            r'\b(?:recommend|suggestion|advice|guidance)\b',
            r'\b(?:best practice|industry standard|benchmark)\b',
            r'\b(?:implement|deployment|rollout|migration)\b',
            r'\b(?:optimize|improvement|enhance|refine)\b'
        ]
        
        # Indicators of simple queries
        self.simple_indicators = [
            r'\b(?:what is|what\'s|define|definition)\b',
            r'\b(?:who is|who\'s)\b',
            r'\b(?:when is|when\'s)\b',
            r'\b(?:where is|where\'s)\b',
            r'\b(?:list|show me|give me)\b'
        ]
        
        # UKG-specific technical terms (medium complexity)
        self.technical_terms = [
            r'\b(?:ukg|pro|wfm|workforce|timekeeper|kronos)\b',
            r'\b(?:accrual|earning|deduction|pay code)\b',
            r'\b(?:hyperfind|business structure|labor level)\b',
            r'\b(?:shift|schedule|badge|punch)\b',
            r'\b(?:api|integration|endpoint|webhook)\b'
        ]
        
        logger.info("Complexity Analyzer initialized")
    
    def analyze(self, query: str, context_sources: int = 0) -> Dict[str, Any]:
        """
        Analyze query complexity and recommend model.
        
        Args:
            query: User's query text
            context_sources: Number of ChromaDB sources available (0 = none)
            
        Returns:
            Dict with:
            - complexity: 'simple', 'medium', or 'complex'
            - model: recommended model name
            - reason: explanation of decision
            - confidence: confidence in classification (0.0 to 1.0)
        """
        if not query:
            return {
                'complexity': 'simple',
                'model': 'mistral:7b',
                'reason': 'Empty query',
                'confidence': 1.0
            }
        
        query_lower = query.lower()
        
        # Calculate various metrics
        word_count = len(query.split())
        sentence_count = len(re.split(r'[.!?]+', query))
        
        # Count indicators
        complex_count = sum(
            1 for pattern in self.complex_indicators
            if re.search(pattern, query_lower, re.IGNORECASE)
        )
        
        simple_count = sum(
            1 for pattern in self.simple_indicators
            if re.search(pattern, query_lower, re.IGNORECASE)
        )
        
        technical_count = sum(
            1 for pattern in self.technical_terms
            if re.search(pattern, query_lower, re.IGNORECASE)
        )
        
        # Score calculation
        complexity_score = 0
        reasons = []
        
        # Word count scoring
        if word_count <= 10:
            complexity_score += 0  # Simple
            reasons.append("short query")
        elif word_count <= 25:
            complexity_score += 1  # Medium
            reasons.append("moderate length")
        else:
            complexity_score += 2  # Complex
            reasons.append("long query")
        
        # Sentence count scoring
        if sentence_count > 2:
            complexity_score += 1
            reasons.append("multi-part question")
        
        # Indicator scoring
        if simple_count > 0:
            complexity_score -= 1
            reasons.append("basic question type")
        
        if complex_count > 0:
            complexity_score += 2
            reasons.append("requires analysis/reasoning")
        
        if technical_count > 2:
            complexity_score += 1
            reasons.append("multiple technical terms")
        
        # Context sources impact
        if context_sources > 5:
            complexity_score += 1
            reasons.append(f"{context_sources} knowledge sources to integrate")
        
        # Question marks (multiple questions = more complex)
        question_marks = query.count('?')
        if question_marks > 1:
            complexity_score += 1
            reasons.append("multiple questions")
        
        # Determine final complexity and model
        if complexity_score <= 0:
            complexity = 'simple'
            model = 'mistral:7b'
            confidence = 0.9
        elif complexity_score <= 2:
            complexity = 'medium'
            model = 'mistral:7b'
            confidence = 0.7
        else:
            complexity = 'complex'
            model = 'deepseek-r1:7b'
            confidence = 0.8
        
        # Build reason string
        reason_str = ', '.join(reasons[:3])  # Top 3 reasons
        
        logger.info(f"Query complexity: {complexity} (score: {complexity_score})")
        
        return {
            'complexity': complexity,
            'model': model,
            'reason': reason_str,
            'confidence': confidence,
            'score': complexity_score,
            'metrics': {
                'word_count': word_count,
                'sentence_count': sentence_count,
                'complex_indicators': complex_count,
                'simple_indicators': simple_count,
                'technical_terms': technical_count
            }
        }
    
    def explain_decision(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate a detailed explanation of the complexity analysis.
        
        Args:
            analysis_result: Result from analyze() method
            
        Returns:
            Human-readable explanation
        """
        complexity = analysis_result['complexity']
        model = analysis_result['model']
        reason = analysis_result['reason']
        confidence = analysis_result['confidence']
        
        explanation = f"""
Query Complexity: {complexity.upper()}
Recommended Model: {model}
Confidence: {confidence:.0%}

Reasoning:
{reason.capitalize()}

Model Selection:
"""
        
        if complexity == 'simple':
            explanation += "- Using Mistral for fast response (3-8 seconds)\n"
            explanation += "- Simple queries don't need deep reasoning\n"
        elif complexity == 'medium':
            explanation += "- Using Mistral for balanced speed/quality (5-15 seconds)\n"
            explanation += "- Medium queries benefit from quick turnaround\n"
        else:
            explanation += "- Using DeepSeek for deep reasoning (25-35 seconds)\n"
            explanation += "- Complex queries need analytical capability\n"
        
        return explanation.strip()
    
    def is_simple_lookup(self, query: str) -> bool:
        """
        Quick check if query is a simple lookup/definition.
        
        Args:
            query: User's query
            
        Returns:
            True if simple lookup
        """
        query_lower = query.lower()
        
        # Check for simple patterns
        for pattern in self.simple_indicators:
            if re.search(pattern, query_lower):
                return True
        
        # Check for very short queries
        if len(query.split()) <= 5:
            return True
        
        return False
    
    def requires_reasoning(self, query: str) -> bool:
        """
        Quick check if query requires deep reasoning.
        
        Args:
            query: User's query
            
        Returns:
            True if reasoning required
        """
        query_lower = query.lower()
        
        # Check for complex patterns
        for pattern in self.complex_indicators:
            if re.search(pattern, query_lower):
                return True
        
        # Check for very long queries
        if len(query.split()) > 30:
            return True
        
        # Check for multiple questions
        if query.count('?') > 2:
            return True
        
        return False


# Convenience functions
def analyze_complexity(query: str, context_sources: int = 0) -> Dict[str, Any]:
    """
    Convenience function to analyze query complexity.
    
    Args:
        query: User's query
        context_sources: Number of ChromaDB sources
        
    Returns:
        Analysis result dict
    """
    analyzer = ComplexityAnalyzer()
    return analyzer.analyze(query, context_sources)


def get_recommended_model(query: str) -> str:
    """
    Get recommended model for query.
    
    Args:
        query: User's query
        
    Returns:
        Model name ('mistral:7b' or 'deepseek-r1:7b')
    """
    analyzer = ComplexityAnalyzer()
    result = analyzer.analyze(query)
    return result['model']
