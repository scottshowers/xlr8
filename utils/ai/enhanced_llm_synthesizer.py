"""
Enhanced LLM Answer Synthesis Module - BUILD 2343
Optimized for UKG implementation analysis with domain-specific prompts
Uses HTTP Basic Auth (same as RAG handler)
Target: 90%+ relevancy and accuracy
"""

import logging
from typing import Dict, List, Any, Optional
import requests
import json
import re
import os

logger = logging.getLogger(__name__)


class EnhancedLLMSynthesizer:
    """
    Enhanced synthesizer with UKG domain knowledge and optimized prompts.
    Designed for 90%+ accuracy on implementation analysis questions.
    """
    
    def __init__(
        self, 
        ollama_base_url: str = "http://178.156.190.64:11435",
        username: str = None,
        password: str = None
    ):
        self.ollama_base_url = ollama_base_url
        self.model = "llama3.2:3b"
        
        # HTTP Basic Auth (same as RAG handler)
        self.ollama_username = username or os.environ.get('LLM_USERNAME', 'xlr8')
        self.ollama_password = password or os.environ.get('LLM_PASSWORD', 'Argyle76226#')
        
        # UKG domain knowledge
        self.domain_knowledge = self._load_domain_knowledge()
        
        # Example question/answer pairs for few-shot learning
        self.examples = self._load_examples()
    
    def _load_domain_knowledge(self) -> str:
        """Load UKG-specific terminology and concepts."""
        return """
UKG DOMAIN KNOWLEDGE:
- Component Company: A legal entity within UKG Pro (like a subsidiary or division)
- FEIN/BN: Federal Employer Identification Number or Business Number (9-digit tax ID)
- Pay Frequency: Weekly (52), Biweekly (26), Semimonthly (24), or Monthly (12) pay periods
- Union: Labor organization requiring special pay rules and reporting
- Pay Group: Collection of employees paid on the same schedule
- Pay Class: Category defining how employees are paid (hourly, salaried, commission)
- Accrual: Earned time off that accumulates (vacation, sick, PTO)
- Timecard: Record of hours worked, typically for hourly employees
- Benefit Plan: Health insurance, 401k, or other employee benefit offering
- Eligibility Rules: Criteria determining who qualifies for benefits
- Waiting Period: Time before new hires become eligible for benefits

IMPORTANT DISTINCTIONS:
- Legal Entity = Component Company (official term in UKG)
- EIN = FEIN = Federal tax ID
- PTO = Paid Time Off (generic term for vacation/sick/personal time)
- Full-time = typically 30-40 hours/week (confirm with customer documents)
- Part-time = typically <30 hours/week (confirm with customer documents)
"""
    
    def _load_examples(self) -> List[Dict[str, str]]:
        """Load example question/answer pairs for few-shot learning."""
        return [
            {
                "question": "Does the customer have multiple legal entities?",
                "context": "According to Company_Structure.pdf, the organization operates three legal entities: ABC Manufacturing Inc (FEIN: 12-3456789), ABC Distribution LLC (FEIN: 98-7654321), and ABC Services Corp (FEIN: 55-6677889).",
                "answer": "Yes, the customer has 3 legal entities (Component Companies in UKG): ABC Manufacturing Inc, ABC Distribution LLC, and ABC Services Corp, each with their own FEIN.",
                "confidence": "95"
            },
            {
                "question": "What pay frequencies does the customer use?",
                "context": "From Payroll_Policy.pdf: Manufacturing employees are paid biweekly, office staff are paid semimonthly, and executives are paid monthly.",
                "answer": "The customer uses three pay frequencies: Biweekly (manufacturing), Semimonthly (office staff), and Monthly (executives). This will require separate Pay Groups in UKG for each frequency.",
                "confidence": "92"
            },
            {
                "question": "Does the customer have any union employees?",
                "context": "The provided documents discuss employee benefits and pay policies but do not mention any unions, collective bargaining agreements, or union contracts.",
                "answer": "The provided customer documents do not contain any information about union employees. This should be confirmed directly with the customer during requirements gathering.",
                "confidence": "85"
            }
        ]
    
    def synthesize_answer(
        self, 
        question: str, 
        chunks: List[str], 
        sources: List[str],
        reason: str = "",
        category: str = "",
        required: bool = False
    ) -> Dict[str, Any]:
        """
        Use LLM to synthesize a clear, accurate answer from RAG chunks.
        
        Args:
            question: The question being answered
            chunks: List of relevant text chunks from RAG
            sources: List of source document names
            reason: Why we're asking this question (context)
            category: Question category (e.g., "Company Structure")
            required: Whether this is a required question
        
        Returns:
            Dict with 'answer', 'confidence', and 'reasoning'
        """
        
        if not chunks:
            return {
                'answer': 'No relevant information found in uploaded customer documents.',
                'confidence': 0.0,
                'reasoning': 'No chunks retrieved from RAG search.'
            }
        
        # Build enhanced prompt
        prompt = self._build_enhanced_prompt(
            question=question,
            chunks=chunks,
            sources=sources,
            reason=reason,
            category=category,
            required=required
        )
        
        # Call LLM with optimized parameters
        try:
            response = self._call_ollama(prompt, temperature=0.2)  # Lower temp = more focused
            
            if response:
                return self._parse_enhanced_response(response)
            else:
                return self._fallback_answer(chunks, sources)
                
        except Exception as e:
            logger.error(f"LLM synthesis error: {e}")
            return self._fallback_answer(chunks, sources)
    
    def _build_enhanced_prompt(
        self,
        question: str,
        chunks: List[str],
        sources: List[str],
        reason: str,
        category: str,
        required: bool
    ) -> str:
        """Build optimized prompt with domain knowledge and examples."""
        
        # Format context from chunks
        context = self._format_context(chunks, sources)
        
        # Build prompt with structure
        prompt = f"""You are an expert UKG implementation consultant analyzing customer documents for a new UKG Pro implementation project.

{self.domain_knowledge}

EXAMPLE ANALYSES (learn from these):
"""
        
        # Add 2 most relevant examples
        for example in self.examples[:2]:
            prompt += f"""
Question: {example['question']}
Context: {example['context']}
Answer: {example['answer']}
Confidence: {example['confidence']}%

"""
        
        prompt += f"""
NOW ANALYZE THIS QUESTION:

QUESTION DETAILS:
- Question: {question}
- Category: {category if category else 'General'}
- Required: {'Yes - This is critical for UKG configuration' if required else 'No'}
{f'- Why We Ask: {reason}' if reason else ''}

CUSTOMER DOCUMENTS RETRIEVED:
{context}

ANALYSIS INSTRUCTIONS:
1. READ ALL CONTEXT CAREFULLY - Every detail matters for UKG configuration
2. ANSWER ONLY FROM PROVIDED DOCUMENTS - Do not add information not present
3. USE UKG TERMINOLOGY - Reference the domain knowledge above
4. BE SPECIFIC - Include names, numbers, policies as stated in documents
5. CITE SOURCES - Reference which document contains each piece of information
6. FLAG MISSING INFO - If documents don't answer the question, explicitly say so
7. IMPLEMENTATION FOCUS - Consider how this answer impacts UKG configuration

ANSWER FORMAT:
Provide your analysis in this exact format:

ANSWER: [Your clear, concise answer using UKG terminology. If information is not in the documents, state "The provided customer documents do not contain this information." Be specific and actionable for UKG configuration.]

SOURCES: [List which documents contained this information]

REASONING: [Brief explanation of how you arrived at this answer, any assumptions made, or concerns about data quality]

CONFIDENCE: [Number from 0-100 indicating your confidence in this answer]

Begin your analysis:
"""
        
        return prompt
    
    def _format_context(self, chunks: List[str], sources: List[str]) -> str:
        """Format chunks with clear source attribution."""
        context = ""
        for i, (chunk, source) in enumerate(zip(chunks, sources), 1):
            # Clean up chunk
            chunk_clean = chunk.strip()
            
            # Add context with clear formatting
            context += f"\n--- SOURCE {i}: {source} ---\n{chunk_clean}\n"
        
        return context
    
    def _call_ollama(self, prompt: str, temperature: float = 0.2, max_tokens: int = 800) -> str:
        """Call Ollama API with optimized parameters for accuracy."""
        
        try:
            from requests.auth import HTTPBasicAuth
            
            url = f"{self.ollama_base_url}/api/generate"
            
            logger.info(f"Calling Ollama at {url} with model {self.model}")
            logger.info(f"Using HTTP Basic Auth with username: {self.ollama_username}")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,  # Lower = more focused/accurate
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1  # Discourage repetition
                }
            }
            
            # Use HTTP Basic Auth (same as RAG handler)
            response = requests.post(
                url, 
                json=payload, 
                auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Ollama synthesis successful")
                return result.get('response', '')
            elif response.status_code == 401:
                logger.error(f"Ollama API authentication failed (401) - check username/password")
                return ""
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return ""
                
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after 120s to {self.ollama_base_url}")
            return ""
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Ollama at {self.ollama_base_url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return ""
    
    def _parse_enhanced_response(self, response: str) -> Dict[str, Any]:
        """Parse structured LLM response."""
        
        # Initialize defaults
        answer = ""
        sources_text = ""
        reasoning = ""
        confidence = 0.7
        
        # Try to parse structured format
        try:
            # Extract ANSWER
            answer_match = re.search(r'ANSWER:\s*(.+?)(?=SOURCES:|REASONING:|CONFIDENCE:|$)', response, re.DOTALL | re.IGNORECASE)
            if answer_match:
                answer = answer_match.group(1).strip()
            
            # Extract SOURCES
            sources_match = re.search(r'SOURCES:\s*(.+?)(?=REASONING:|CONFIDENCE:|$)', response, re.DOTALL | re.IGNORECASE)
            if sources_match:
                sources_text = sources_match.group(1).strip()
            
            # Extract REASONING
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?=CONFIDENCE:|$)', response, re.DOTALL | re.IGNORECASE)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            # Extract CONFIDENCE
            conf_match = re.search(r'CONFIDENCE:\s*(\d+)', response, re.IGNORECASE)
            if conf_match:
                confidence = float(conf_match.group(1)) / 100.0
                confidence = max(0.0, min(1.0, confidence))
        
        except Exception as e:
            logger.warning(f"Error parsing structured response: {e}")
            # Fall back to using entire response as answer
            answer = response.strip()
        
        # If no structured answer found, use full response
        if not answer:
            answer = response.strip()
        
        # Clean up answer
        answer = self._clean_answer(answer)
        
        return {
            'answer': answer,
            'confidence': confidence,
            'reasoning': reasoning if reasoning else "Analysis based on provided customer documents"
        }
    
    def _clean_answer(self, answer: str) -> str:
        """Clean up LLM answer text."""
        # Remove markdown formatting
        answer = answer.replace("**", "").replace("__", "")
        
        # Remove any leftover prompt artifacts
        answer = re.sub(r'(ANSWER:|SOURCES:|REASONING:|CONFIDENCE:)', '', answer, flags=re.IGNORECASE)
        
        # Clean up whitespace
        answer = re.sub(r'\n\s*\n', '\n\n', answer)
        answer = answer.strip()
        
        return answer
    
    def _fallback_answer(self, chunks: List[str], sources: List[str]) -> Dict[str, Any]:
        """Fallback answer if LLM fails."""
        
        parts = []
        for chunk, source in zip(chunks[:2], sources[:2]):  # Only top 2
            parts.append(f"**From {source}:**\n{chunk[:250]}...")
        
        return {
            'answer': "\n\n".join(parts),
            'confidence': 0.5,
            'reasoning': "LLM synthesis failed - showing raw chunks"
        }


# Singleton instance
_enhanced_synthesizer = None

def get_enhanced_synthesizer() -> EnhancedLLMSynthesizer:
    """Get or create enhanced synthesizer instance with auth from environment."""
    global _enhanced_synthesizer
    if _enhanced_synthesizer is None:
        import os
        
        # Read configuration from environment (matches RAG handler)
        ollama_url = os.environ.get('LLM_ENDPOINT', 'http://178.156.190.64:11435')
        username = os.environ.get('LLM_USERNAME', 'xlr8')
        password = os.environ.get('LLM_PASSWORD', 'Argyle76226#')
        
        _enhanced_synthesizer = EnhancedLLMSynthesizer(
            ollama_base_url=ollama_url,
            username=username,
            password=password
        )
    return _enhanced_synthesizer
