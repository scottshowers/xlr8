"""
LLM Answer Synthesis Module
Uses local LLM to synthesize intelligent answers from RAG chunks
"""

import logging
from typing import Dict, List, Any
import requests
import json

logger = logging.getLogger(__name__)


class LLMSynthesizer:
    """Synthesizes answers from RAG chunks using local LLM."""
    
    def __init__(self, ollama_base_url: str = "http://176.58.122.95:11434"):
        self.ollama_base_url = ollama_base_url
        self.model = "llama3.2:3b"
    
    def synthesize_answer(
        self, 
        question: str, 
        chunks: List[str], 
        sources: List[str],
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Use LLM to synthesize a clear answer from RAG chunks.
        
        Args:
            question: The question being answered
            chunks: List of relevant text chunks from RAG
            sources: List of source document names
            reason: Why we're asking this question (context)
        
        Returns:
            Dict with 'answer' and 'confidence'
        """
        
        if not chunks:
            return {
                'answer': 'No relevant information found in uploaded documents.',
                'confidence': 0.0
            }
        
        # Build prompt for LLM
        prompt = self._build_synthesis_prompt(question, chunks, sources, reason)
        
        # Call LLM
        try:
            response = self._call_ollama(prompt)
            
            if response:
                # Extract answer and confidence from LLM response
                return self._parse_llm_response(response)
            else:
                # Fallback to concatenated chunks
                return {
                    'answer': self._fallback_answer(chunks, sources),
                    'confidence': 0.5
                }
                
        except Exception as e:
            logger.error(f"LLM synthesis error: {e}")
            return {
                'answer': self._fallback_answer(chunks, sources),
                'confidence': 0.4
            }
    
    def _build_synthesis_prompt(
        self, 
        question: str, 
        chunks: List[str], 
        sources: List[str],
        reason: str
    ) -> str:
        """Build a clear prompt for the LLM."""
        
        # Format chunks with sources
        context = ""
        for i, (chunk, source) in enumerate(zip(chunks, sources), 1):
            context += f"\n[Source {i}: {source}]\n{chunk}\n"
        
        prompt = f"""You are analyzing customer documents to answer UKG implementation questions.

QUESTION:
{question}

{f"WHY WE ASK: {reason}" if reason else ""}

RELEVANT INFORMATION FROM CUSTOMER DOCUMENTS:
{context}

INSTRUCTIONS:
1. Answer the question clearly and concisely based ONLY on the information provided above
2. If the documents contain the answer, provide it in 2-4 sentences
3. Cite which source(s) contain the information (e.g., "According to [Source 1]...")
4. If the information is partial or unclear, say so
5. If the documents don't answer the question, say "The provided documents do not contain this information"
6. After your answer, on a new line, rate your confidence from 0-100 in this format: CONFIDENCE: XX

ANSWER:"""
        
        return prompt
    
    def _call_ollama(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Ollama API to generate response."""
        
        try:
            url = f"{self.ollama_base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower = more focused
                    "num_predict": max_tokens,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""
                
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return ""
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return ""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract answer and confidence."""
        
        # Look for confidence rating
        confidence = 0.7  # Default
        answer = response.strip()
        
        # Check for CONFIDENCE: XX pattern
        if "CONFIDENCE:" in answer.upper():
            parts = answer.split("CONFIDENCE:")
            if len(parts) == 2:
                answer = parts[0].strip()
                try:
                    conf_str = parts[1].strip().split()[0]
                    confidence = float(conf_str) / 100.0
                    confidence = max(0.0, min(1.0, confidence))
                except:
                    confidence = 0.7
        
        # Remove any markdown formatting if present
        answer = answer.replace("**", "").replace("__", "")
        
        return {
            'answer': answer,
            'confidence': confidence
        }
    
    def _fallback_answer(self, chunks: List[str], sources: List[str]) -> str:
        """Fallback answer if LLM fails - concatenate chunks."""
        
        parts = []
        for chunk, source in zip(chunks[:3], sources[:3]):
            parts.append(f"**From {source}:**\n{chunk[:300]}...")
        
        return "\n\n".join(parts)


# Singleton instance
_synthesizer = None

def get_synthesizer() -> LLMSynthesizer:
    """Get or create synthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = LLMSynthesizer()
    return _synthesizer
