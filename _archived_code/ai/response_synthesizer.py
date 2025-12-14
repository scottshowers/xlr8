"""
Response Synthesizer - Combines Multiple Sources for Final Response

Handles:
- Combining ChromaDB context with LLM responses
- Formatting final responses for users
- Source attribution and tracking
- Context enhancement

FIXES IN THIS VERSION:
- Extracts actual filenames from metadata.source (not text content)
- Shows project_id for each source document
- Better relevance scoring display
- Improved source formatting

Author: HCMPACT
Version: 1.1 - Project Isolation & Better Source Display
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
    """
    Synthesizes responses from multiple sources.
    
    Combines:
    - LLM-generated responses
    - ChromaDB context
    - Source attribution
    - Formatting
    """
    
    def __init__(self):
        """Initialize the response synthesizer"""
        logger.info("Response Synthesizer initialized")
    
    def synthesize(self,
                  llm_response: str,
                  chromadb_context: Optional[List[Dict]] = None,
                  model_used: str = "unknown",
                  has_pii_protection: bool = False,
                  complexity: str = "medium",
                  processing_time: float = 0.0) -> SynthesizedResponse:
        """
        Synthesize a final response from LLM output and optional context.
        
        Args:
            llm_response: Raw response from LLM
            chromadb_context: Optional list of ChromaDB sources used
            model_used: Name of the model that generated the response
            has_pii_protection: Whether PII protection was applied
            complexity: Query complexity level
            processing_time: Total processing time in seconds
            
        Returns:
            SynthesizedResponse object
        """
        # Clean up the LLM response
        cleaned_response = self._clean_response(llm_response)
        
        # Format sources if available
        formatted_sources = []
        if chromadb_context:
            formatted_sources = self._format_sources(chromadb_context)
        
        # Determine confidence level
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
        """
        Clean up LLM response text.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Cleaned response text
        """
        if not response:
            return "I apologize, but I wasn't able to generate a response. Please try rephrasing your question."
        
        # Remove extra whitespace
        response = response.strip()
        
        # Remove any markdown artifacts that shouldn't be there
        # (but keep intentional formatting)
        
        return response
    
    def _format_sources(self, chromadb_context: List[Dict]) -> List[Dict[str, Any]]:
        """
        Format ChromaDB sources for display.
        
        FIXED: Now extracts actual filenames from metadata instead of showing text content
        
        Args:
            chromadb_context: Raw ChromaDB context
            
        Returns:
            Formatted source list
        """
        formatted = []
        
        for idx, source in enumerate(chromadb_context, 1):
            # Extract metadata
            metadata = source.get('metadata', {})
            
            # Get actual filename from metadata (not the text content)
            filename = metadata.get('source', source.get('document', 'Unknown'))
            
            # Get project if available
            project_id = metadata.get('project_id')
            
            # Get the actual text content for excerpts
            content = source.get('document', source.get('content', ''))
            
            # Build category display
            category = source.get('category', 'General')
            if project_id:
                category = f"Project: {project_id}"
            elif metadata.get('file_type'):
                category = f"{metadata.get('file_type').upper()} Document"
            
            formatted_source = {
                'index': idx,
                'document_name': filename,  # ← Now shows actual filename
                'category': category,  # ← Now shows project or file type
                'project_id': project_id,  # ← Track project for filtering
                'relevance_score': source.get('distance', 0.0),
                'excerpt': self._create_excerpt(content),  # ← Use actual content for excerpt
                'metadata': metadata  # ← Keep full metadata
            }
            formatted.append(formatted_source)
        
        return formatted
    
    def _create_excerpt(self, content: str, max_length: int = 150) -> str:
        """
        Create a short excerpt from content.
        
        Args:
            content: Full content text
            max_length: Maximum excerpt length
            
        Returns:
            Excerpt string
        """
        if not content:
            return ""
        
        if len(content) <= max_length:
            return content
        
        # Try to break at a sentence
        excerpt = content[:max_length]
        last_period = excerpt.rfind('.')
        
        if last_period > max_length * 0.6:  # If we can break at a reasonable sentence
            return excerpt[:last_period + 1]
        else:
            return excerpt[:max_length].rsplit(' ', 1)[0] + "..."
    
    def _assess_confidence(self,
                          llm_response: str,
                          has_context: bool,
                          complexity: str) -> str:
        """
        Assess confidence level of the response.
        
        Args:
            llm_response: The generated response
            has_context: Whether ChromaDB context was available
            complexity: Query complexity
            
        Returns:
            Confidence level: "high", "medium", or "low"
        """
        # High confidence: Has context and is a simple/medium query
        if has_context and complexity in ['simple', 'medium']:
            return "high"
        
        # Medium confidence: Has context but complex, or no context but simple
        if (has_context and complexity == 'complex') or (not has_context and complexity == 'simple'):
            return "medium"
        
        # Low confidence: No context and medium/complex query
        return "low"
    
    def build_enhanced_prompt(self,
                            user_query: str,
                            chromadb_context: Optional[List[Dict]] = None,
                            system_context: Optional[str] = None) -> str:
        """
        Build an enhanced prompt that includes ChromaDB context.
        
        Args:
            user_query: Original user query
            chromadb_context: Optional ChromaDB sources
            system_context: Optional system-level context
            
        Returns:
            Enhanced prompt string
        """
        prompt_parts = []
        
        # Add system context if provided
        if system_context:
            prompt_parts.append(f"SYSTEM CONTEXT:\n{system_context}\n")
        
        # Add ChromaDB context if available
        if chromadb_context and len(chromadb_context) > 0:
            prompt_parts.append("RELEVANT HCMPACT KNOWLEDGE:\n")
            
            for idx, source in enumerate(chromadb_context, 1):
                # Extract filename from metadata (not from 'document' which is content)
                metadata = source.get('metadata', {})
                doc_name = metadata.get('source', 'Unknown Document')
                
                # Get project info if available
                project_id = metadata.get('project_id')
                if project_id:
                    category = f"Project: {project_id}"
                else:
                    category = source.get('category', 'General')
                
                # Get the actual text content
                content = source.get('document', source.get('content', ''))
                
                prompt_parts.append(f"\n[Source {idx}: {doc_name} - {category}]")
                prompt_parts.append(content)
                prompt_parts.append("")
            
            prompt_parts.append("\n---\n")
        
        # Add user query
        prompt_parts.append(f"USER QUESTION:\n{user_query}\n")
        
        # Add DETAILED instructions for comprehensive responses
        if chromadb_context:
            prompt_parts.append("\nINSTRUCTIONS:")
            prompt_parts.append("Using the HCMPACT knowledge provided above, provide a DETAILED, COMPREHENSIVE answer.")
            prompt_parts.append("")
            prompt_parts.append("CRITICAL REQUIREMENTS:")
            prompt_parts.append("1. If the question asks HOW to do something, provide COMPLETE step-by-step instructions")
            prompt_parts.append("   - Include EVERY step, numbered sequentially")
            prompt_parts.append("   - Specify exact navigation paths (e.g., 'Go to Menu > Section > Subsection')")
            prompt_parts.append("   - Include field names, button labels, and form locations")
            prompt_parts.append("   - Add notes about common options or variations")
            prompt_parts.append("")
            prompt_parts.append("2. If the question asks WHAT something is, provide:")
            prompt_parts.append("   - Complete definition with context")
            prompt_parts.append("   - Purpose and use cases")
            prompt_parts.append("   - Related concepts or dependencies")
            prompt_parts.append("   - Practical examples where applicable")
            prompt_parts.append("")
            prompt_parts.append("3. DO NOT give high-level overviews or summaries")
            prompt_parts.append("   - Users need actionable, specific details they can follow")
            prompt_parts.append("   - 5 general steps is NOT enough - provide 10-15+ detailed steps if needed")
            prompt_parts.append("   - Include screenshots references, field names, validation rules")
            prompt_parts.append("")
            prompt_parts.append("4. Reference the source documents when providing information")
            prompt_parts.append("   - Cite which source contains specific details")
            prompt_parts.append("   - If sources don't fully answer the question, acknowledge what's missing")
            prompt_parts.append("")
            prompt_parts.append("5. Structure your response clearly:")
            prompt_parts.append("   - Use headers, numbered lists, and bullet points")
            prompt_parts.append("   - Break complex procedures into logical sections")
            prompt_parts.append("   - Add 'Notes' or 'Tips' sections for important context")
        else:
            # No context available - still demand detailed responses
            prompt_parts.append("\nINSTRUCTIONS:")
            prompt_parts.append("Provide a DETAILED, COMPREHENSIVE answer using your general knowledge.")
            prompt_parts.append("")
            prompt_parts.append("CRITICAL REQUIREMENTS:")
            prompt_parts.append("1. If the question asks HOW to do something:")
            prompt_parts.append("   - Provide COMPLETE step-by-step instructions (10-15+ steps)")
            prompt_parts.append("   - Include exact navigation paths where possible")
            prompt_parts.append("   - Specify field names, buttons, and form locations")
            prompt_parts.append("   - DO NOT give 5 high-level steps - provide detailed, actionable steps")
            prompt_parts.append("")
            prompt_parts.append("2. If the question asks WHAT something is:")
            prompt_parts.append("   - Complete definition with context")
            prompt_parts.append("   - Purpose and use cases")
            prompt_parts.append("   - Related concepts")
            prompt_parts.append("   - Practical examples")
            prompt_parts.append("")
            prompt_parts.append("3. Structure your response clearly:")
            prompt_parts.append("   - Use headers, numbered lists, and bullet points")
            prompt_parts.append("   - Break complex procedures into logical sections")
            prompt_parts.append("   - Add notes for important details")
            prompt_parts.append("")
            prompt_parts.append("4. If the question is specific to UKG Pro/WFM:")
            prompt_parts.append("   - Provide as much detail as possible from general UKG knowledge")
            prompt_parts.append("   - Note at the END if HCMPACT-specific documentation would provide additional implementation details")
        
        return "\n".join(prompt_parts)
    
    def format_for_display(self,
                          response: SynthesizedResponse,
                          show_metadata: bool = True,
                          show_sources: bool = True) -> str:
        """
        Format a synthesized response for display to user.
        
        Args:
            response: SynthesizedResponse object
            show_metadata: Whether to show metadata (model, time, etc.)
            show_sources: Whether to show source list
            
        Returns:
            Formatted response string
        """
        output_parts = []
        
        # Main response text
        output_parts.append(response.text)
        
        # Add metadata if requested
        if show_metadata:
            output_parts.append("\n\n---\n")
            
            metadata_lines = []
            
            # Model and processing time
            metadata_lines.append(f"**Model:** {response.model_used}")
            metadata_lines.append(f"**Response Time:** {response.processing_time:.1f}s")
            metadata_lines.append(f"**Complexity:** {response.complexity.capitalize()}")
            
            if response.confidence_level:
                confidence_emoji = {
                    'high': '',
                    'medium': '',
                    'low': ''
                }
                emoji = confidence_emoji.get(response.confidence_level, '')
                metadata_lines.append(f"**Confidence:** {emoji} {response.confidence_level.capitalize()}")
            
            if response.has_pii_protection:
                metadata_lines.append("**Security:**  PII Protection Active")
            
            output_parts.append("\n".join(metadata_lines))
        
        # Add sources if requested and available
        if show_sources and response.sources:
            output_parts.append("\n\n**📚 Sources Used:**\n")
            
            for source in response.sources:
                # Build source line with filename and category
                source_line = f"{source['index']}. **{source['document_name']}**"
                
                # Add project tag if available
                if source.get('project_id'):
                    source_line += f" (📁 {source['project_id']})"
                elif source.get('category') and source['category'] != 'General':
                    source_line += f" ({source['category']})"
                
                # Add relevance score
                if source.get('relevance_score') is not None:
                    # Convert distance to similarity percentage (lower distance = higher similarity)
                    similarity = (1.0 - min(source['relevance_score'], 1.0)) * 100
                    source_line += f" - {similarity:.0f}% match"
                
                output_parts.append(source_line)
                
                # Add excerpt if available
                if source.get('excerpt'):
                    output_parts.append(f"   _{source['excerpt']}_\n")
                else:
                    output_parts.append("")
        
        return "\n".join(output_parts)
    
    def create_citation(self, source: Dict[str, Any], index: int) -> str:
        """
        Create a citation string for a source.
        
        Args:
            source: Source dict
            index: Source index number
            
        Returns:
            Citation string
        """
        doc_name = source.get('document_name', source.get('document', 'Unknown'))
        category = source.get('category', 'General')
        
        return f"[{index}] {doc_name} ({category})"


# Convenience functions
def synthesize_response(llm_response: str,
                       chromadb_context: Optional[List[Dict]] = None,
                       **kwargs) -> SynthesizedResponse:
    """
    Convenience function to synthesize a response.
    
    Args:
        llm_response: LLM-generated text
        chromadb_context: Optional ChromaDB sources
        **kwargs: Additional arguments
        
    Returns:
        SynthesizedResponse object
    """
    synthesizer = ResponseSynthesizer()
    return synthesizer.synthesize(llm_response, chromadb_context, **kwargs)


def build_prompt_with_context(user_query: str,
                              chromadb_context: Optional[List[Dict]] = None,
                              system_context: Optional[str] = None) -> str:
    """
    Convenience function to build an enhanced prompt.
    
    Args:
        user_query: User's query
        chromadb_context: Optional ChromaDB sources
        system_context: Optional system context
        
    Returns:
        Enhanced prompt string
    """
    synthesizer = ResponseSynthesizer()
    return synthesizer.build_enhanced_prompt(user_query, chromadb_context, system_context)
