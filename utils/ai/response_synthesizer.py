"""
Response Synthesizer - Fixed version
Properly formats ChromaDB sources and relevance scores
"""

from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SynthesizedResponse:
    """A synthesized response with all metadata"""
    text: str
    sources: List[Dict[str, Any]]
    model_used: str
    has_pii_protection: bool
    complexity: str
    processing_time: float
    confidence_level: Optional[str] = None


class ResponseSynthesizer:
    """Synthesizes responses from multiple sources"""
    
    def __init__(self):
        logger.info("Response Synthesizer initialized")
    
    def synthesize(self,
                  llm_response: str,
                  chromadb_context: Optional[List[Dict]] = None,
                  model_used: str = "unknown",
                  has_pii_protection: bool = False,
                  complexity: str = "medium",
                  processing_time: float = 0.0) -> SynthesizedResponse:
        """Synthesize final response"""
        
        cleaned_response = self._clean_response(llm_response)
        
        formatted_sources = []
        if chromadb_context:
            formatted_sources = self._format_sources(chromadb_context)
        
        confidence = self._assess_confidence(
            llm_response=cleaned_response,
            has_context=bool(chromadb_context),
            complexity=complexity
        )
        
        return SynthesizedResponse(
            text=cleaned_response,
            sources=formatted_sources,
            model_used=model_used,
            has_pii_protection=has_pii_protection,
            complexity=complexity,
            processing_time=processing_time,
            confidence_level=confidence
        )
    
    def _clean_response(self, response: str) -> str:
        """Clean up LLM response"""
        if not response:
            return "I apologize, but I wasn't able to generate a response."
        return response.strip()
    
    def _format_sources(self, chromadb_context: List[Dict]) -> List[Dict[str, Any]]:
        """Format ChromaDB sources - FIXED to handle actual structure"""
        formatted = []
        
        for idx, source in enumerate(chromadb_context, 1):
            # Extract metadata properly
            metadata = source.get('metadata', {})
            doc_name = metadata.get('doc_name', metadata.get('name', 'Unknown Document'))
            category = metadata.get('category', 'General')
            
            # Convert distance to similarity percentage (0 distance = 100% similar)
            distance = source.get('distance', 1.0)
            similarity = max(0, min(100, (1.0 - distance) * 100))
            
            formatted_source = {
                'index': idx,
                'document_name': doc_name,
                'category': category,
                'relevance_score': similarity,
                'excerpt': self._create_excerpt(source.get('content', '')),
                'metadata': metadata
            }
            formatted.append(formatted_source)
        
        return formatted
    
    def _create_excerpt(self, content: str, max_length: int = 150) -> str:
        """Create short excerpt"""
        if not content:
            return ""
        
        if len(content) <= max_length:
            return content
        
        excerpt = content[:max_length]
        last_period = excerpt.rfind('.')
        
        if last_period > max_length * 0.6:
            return excerpt[:last_period + 1]
        else:
            return excerpt[:max_length].rsplit(' ', 1)[0] + "..."
    
    def _assess_confidence(self, llm_response: str, has_context: bool, complexity: str) -> str:
        """Assess confidence level"""
        if has_context and complexity in ['simple', 'medium']:
            return "high"
        if (has_context and complexity == 'complex') or (not has_context and complexity == 'simple'):
            return "medium"
        return "low"
    
    def build_enhanced_prompt(self,
                            user_query: str,
                            chromadb_context: Optional[List[Dict]] = None,
                            system_context: Optional[str] = None) -> str:
        """Build enhanced prompt with context"""
        prompt_parts = []
        
        if system_context:
            prompt_parts.append(f"SYSTEM CONTEXT:\n{system_context}\n")
        
        if chromadb_context and len(chromadb_context) > 0:
            prompt_parts.append("RELEVANT HCMPACT KNOWLEDGE:\n")
            
            for idx, source in enumerate(chromadb_context, 1):
                metadata = source.get('metadata', {})
                doc_name = metadata.get('doc_name', metadata.get('name', 'Unknown'))
                category = metadata.get('category', 'General')
                content = source.get('content', '')
                
                prompt_parts.append(f"\n[Source {idx}: {doc_name} - {category}]")
                prompt_parts.append(content)
                prompt_parts.append("")
            
            prompt_parts.append("\n---\n")
        
        prompt_parts.append(f"USER QUESTION:\n{user_query}\n")
        
        if chromadb_context:
            prompt_parts.append("\nINSTRUCTIONS:")
            prompt_parts.append("Answer using the HCMPACT knowledge above.")
            prompt_parts.append("Reference specific sources when using information from them.")
            prompt_parts.append("If sources don't fully answer, acknowledge what's covered.")
        
        return "\n".join(prompt_parts)
