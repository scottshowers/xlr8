"""
LLM Orchestrator for XLR8
=========================

MULTI-MODEL ARCHITECTURE:
1. Local LLMs (Mistral, DeepSeek) - Can see PII, handle raw document data
2. Claude - Synthesis only, NEVER sees PII

FLOW:
1. User query → Search ChromaDB for chunks
2. Chunks + query → Local LLM (full context, can see PII)
3. Local LLM output → SANITIZE (strip all PII)
4. Sanitized output → Claude for final synthesis
5. Return response to user

PRIVACY RULES:
- NO names, SSNs, salaries, addresses go to Claude
- Only sanitized summaries and analysis
- All PII stays on local Hetzner server

Author: XLR8 Team
"""

import os
import re
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Available model types"""
    MISTRAL = "mistral"      # General analysis, HR content
    DEEPSEEK = "deepseek"    # Data analysis, technical content
    CLAUDE = "claude"        # Synthesis (sanitized only!)


class PIISanitizer:
    """
    Sanitizes text to remove PII before sending to Claude
    
    REMOVES:
    - Names (replaces with Employee A, B, C...)
    - SSNs (XXX-XX-XXXX pattern)
    - Phone numbers
    - Email addresses
    - Specific salary/dollar amounts (replaces with ranges)
    - Addresses
    - Account numbers
    - Dates of birth
    """
    
    # Common name patterns to detect
    NAME_INDICATORS = [
        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
        r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b',  # First M. Last
    ]
    
    # PII patterns
    SSN_PATTERN = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
    PHONE_PATTERN = r'\b(?:\+1[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    DOLLAR_PATTERN = r'\$[\d,]+(?:\.\d{2})?'
    ADDRESS_PATTERN = r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Boulevard|Blvd)\b'
    DOB_PATTERN = r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'
    ACCOUNT_PATTERN = r'\b(?:account|acct|routing)[\s#:]*\d{4,}\b'
    
    def __init__(self):
        self.name_counter = 0
        self.name_map = {}  # Track replaced names for consistency
        
    def _get_employee_placeholder(self, name: str) -> str:
        """Get consistent placeholder for a name"""
        if name not in self.name_map:
            self.name_counter += 1
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            idx = (self.name_counter - 1) % 26
            suffix = "" if self.name_counter <= 26 else str(self.name_counter // 26)
            self.name_map[name] = f"[Employee {letters[idx]}{suffix}]"
        return self.name_map[name]
    
    def _replace_names(self, text: str) -> str:
        """Replace potential names with placeholders"""
        result = text
        for pattern in self.NAME_INDICATORS:
            matches = re.findall(pattern, result)
            for match in matches:
                # Skip common non-name phrases
                if match.lower() in ['new york', 'los angeles', 'san francisco', 'united states']:
                    continue
                placeholder = self._get_employee_placeholder(match)
                result = result.replace(match, placeholder)
        return result
    
    def _replace_ssn(self, text: str) -> str:
        """Replace SSNs with placeholder"""
        return re.sub(self.SSN_PATTERN, '[SSN REDACTED]', text)
    
    def _replace_phone(self, text: str) -> str:
        """Replace phone numbers with placeholder"""
        return re.sub(self.PHONE_PATTERN, '[PHONE REDACTED]', text)
    
    def _replace_email(self, text: str) -> str:
        """Replace emails with placeholder"""
        return re.sub(self.EMAIL_PATTERN, '[EMAIL REDACTED]', text)
    
    def _replace_dollars(self, text: str) -> str:
        """Replace specific dollar amounts with ranges"""
        def dollar_to_range(match):
            amount_str = match.group(0).replace('$', '').replace(',', '')
            try:
                amount = float(amount_str)
                if amount < 1000:
                    return "[under $1K]"
                elif amount < 10000:
                    return "[~$1K-10K range]"
                elif amount < 50000:
                    return "[~$10K-50K range]"
                elif amount < 100000:
                    return "[~$50K-100K range]"
                elif amount < 250000:
                    return "[~$100K-250K range]"
                else:
                    return "[~$250K+ range]"
            except:
                return "[AMOUNT REDACTED]"
        
        return re.sub(self.DOLLAR_PATTERN, dollar_to_range, text)
    
    def _replace_address(self, text: str) -> str:
        """Replace addresses with placeholder"""
        return re.sub(self.ADDRESS_PATTERN, '[ADDRESS REDACTED]', text, flags=re.IGNORECASE)
    
    def _replace_dob(self, text: str) -> str:
        """Replace dates of birth with placeholder"""
        return re.sub(self.DOB_PATTERN, '[DOB REDACTED]', text)
    
    def _replace_accounts(self, text: str) -> str:
        """Replace account numbers with placeholder"""
        return re.sub(self.ACCOUNT_PATTERN, '[ACCOUNT REDACTED]', text, flags=re.IGNORECASE)
    
    def sanitize(self, text: str) -> str:
        """
        Full sanitization pipeline
        
        Returns text safe to send to Claude (no PII)
        """
        if not text:
            return text
            
        result = text
        
        # Order matters - do names last as they're trickiest
        result = self._replace_ssn(result)
        result = self._replace_phone(result)
        result = self._replace_email(result)
        result = self._replace_dob(result)
        result = self._replace_accounts(result)
        result = self._replace_address(result)
        result = self._replace_dollars(result)
        result = self._replace_names(result)
        
        return result
    
    def reset(self):
        """Reset name mappings for new conversation"""
        self.name_counter = 0
        self.name_map = {}


class LLMOrchestrator:
    """
    Orchestrates multi-model LLM calls with privacy protection
    
    ARCHITECTURE:
    - Local LLMs (Ollama on Hetzner): Handle raw data with PII
    - Claude (API): Synthesis only, sanitized data only
    """
    
    def __init__(self):
        # Ollama configuration (Hetzner)
        self.ollama_url = os.getenv("LLM_ENDPOINT", "http://178.156.190.64:11435")
        self.ollama_username = os.getenv("LLM_USERNAME", "xlr8")
        self.ollama_password = os.getenv("LLM_PASSWORD", "Argyle76226#")
        
        # Model names on Ollama
        self.mistral_model = os.getenv("MISTRAL_MODEL", "mistral:latest")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-coder:6.7b")
        
        # Claude configuration
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_model = "claude-sonnet-4-20250514"
        
        # Sanitizer
        self.sanitizer = PIISanitizer()
        
        logger.info(f"LLMOrchestrator initialized")
        logger.info(f"  Ollama: {self.ollama_url}")
        logger.info(f"  Mistral: {self.mistral_model}")
        logger.info(f"  DeepSeek: {self.deepseek_model}")
        logger.info(f"  Claude: {'enabled' if self.claude_api_key else 'disabled'}")
    
    def _call_ollama(self, model: str, prompt: str, system_prompt: str = None) -> Tuple[str, bool]:
        """
        Call Ollama (Mistral or DeepSeek)
        
        Returns: (response_text, success)
        """
        try:
            url = f"{self.ollama_url}/api/generate"
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048
                }
            }
            
            logger.info(f"Calling Ollama model: {model}")
            
            response = requests.post(
                url,
                json=payload,
                auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text}")
                return f"Error from {model}: {response.status_code}", False
            
            result = response.json()
            return result.get("response", ""), True
            
        except requests.exceptions.Timeout:
            logger.error(f"Ollama timeout for {model}")
            return f"Timeout calling {model}", False
        except Exception as e:
            logger.error(f"Ollama error for {model}: {e}")
            return f"Error: {str(e)}", False
    
    def _call_claude(self, prompt: str, system_prompt: str = None) -> Tuple[str, bool]:
        """
        Call Claude API
        
        IMPORTANT: Only receives SANITIZED data!
        
        Returns: (response_text, success)
        """
        if not self.claude_api_key:
            logger.warning("Claude API key not configured")
            return "Claude not configured", False
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_api_key)
            
            messages = [{"role": "user", "content": prompt}]
            
            response = client.messages.create(
                model=self.claude_model,
                max_tokens=2048,
                system=system_prompt or "You are a helpful HCM implementation consultant.",
                messages=messages
            )
            
            logger.info("Claude response received")
            return response.content[0].text, True
            
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return f"Claude error: {str(e)}", False
    
    def _determine_local_model(self, query: str, chunks: List[Dict]) -> str:
        """
        Determine which local model to use based on query content
        
        Mistral: General HR, policy, document understanding
        DeepSeek: Data analysis, code, technical queries, calculations
        """
        query_lower = query.lower()
        
        # DeepSeek indicators (data/technical focus)
        deepseek_keywords = [
            'calculate', 'compute', 'formula', 'code', 'script',
            'data', 'analysis', 'spreadsheet', 'excel', 'csv',
            'sum', 'average', 'total', 'count', 'percentage',
            'compare', 'difference', 'trend', 'statistics'
        ]
        
        # Check query for DeepSeek indicators
        for keyword in deepseek_keywords:
            if keyword in query_lower:
                logger.info(f"Routing to DeepSeek (keyword: {keyword})")
                return self.deepseek_model
        
        # Check if chunks are mostly tabular data
        if chunks:
            tabular_count = sum(1 for c in chunks if c.get('metadata', {}).get('chunk_type') == 'table_row')
            if tabular_count > len(chunks) / 2:
                logger.info("Routing to DeepSeek (tabular data)")
                return self.deepseek_model
        
        # Default to Mistral for general queries
        logger.info("Routing to Mistral (general query)")
        return self.mistral_model
    
    def process_query(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        use_claude_synthesis: bool = True
    ) -> Dict[str, Any]:
        """
        Main orchestration method
        
        FLOW:
        1. Route to appropriate local LLM (can see full PII)
        2. Local LLM analyzes and responds
        3. SANITIZE the response
        4. Send to Claude for synthesis (if enabled)
        5. Return final response
        
        Args:
            query: User's question
            chunks: Retrieved document chunks (contain PII)
            use_claude_synthesis: Whether to use Claude for final synthesis
            
        Returns:
            Dict with response, sources, models_used, etc.
        """
        self.sanitizer.reset()  # Fresh name mappings
        
        result = {
            "response": "",
            "models_used": [],
            "local_analysis": "",
            "sanitized": False,
            "error": None
        }
        
        # Step 1: Build context from chunks (CONTAINS PII)
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get('metadata', {}).get('source', 'Unknown')
            text = chunk.get('document', chunk.get('text', ''))
            context_parts.append(f"[Document {i}: {source}]\n{text}")
        
        full_context = "\n\n---\n\n".join(context_parts)
        
        # Step 2: Determine which local model to use
        local_model = self._determine_local_model(query, chunks)
        
        # Step 3: Build prompt for local LLM (can see everything)
        local_system_prompt = """You are an expert HCM implementation consultant analyzing customer documents.
Your task is to analyze the provided documents and answer the user's question accurately.

IMPORTANT RULES:
1. Be specific and cite which document your information comes from
2. If analyzing employee data, provide accurate details
3. If you find specific names, salaries, or other data - include them in your analysis
4. Be thorough but concise

Analyze the documents and provide a detailed answer."""

        local_user_prompt = f"""Based on the following documents, please answer this question:

QUESTION: {query}

DOCUMENTS:
{full_context}

Provide a detailed, accurate answer based on the documents above."""

        # Step 4: Call local LLM
        logger.info(f"Step 1: Calling local LLM ({local_model})")
        local_response, local_success = self._call_ollama(
            local_model, 
            local_user_prompt, 
            local_system_prompt
        )
        
        result["models_used"].append(local_model)
        result["local_analysis"] = local_response
        
        if not local_success:
            result["error"] = f"Local LLM failed: {local_response}"
            result["response"] = local_response
            return result
        
        # Step 5: SANITIZE the local response before Claude
        logger.info("Step 2: Sanitizing response (removing PII)")
        sanitized_response = self.sanitizer.sanitize(local_response)
        result["sanitized"] = True
        
        # Log what was sanitized (for debugging)
        if sanitized_response != local_response:
            logger.info(f"PII removed: {len(self.sanitizer.name_map)} names replaced")
        
        # Step 6: If Claude synthesis enabled, send sanitized data
        if use_claude_synthesis and self.claude_api_key:
            logger.info("Step 3: Calling Claude for synthesis (sanitized data only)")
            
            claude_system_prompt = """You are an expert HCM implementation consultant.
You are receiving a SANITIZED analysis from a local AI that has already reviewed the customer's documents.
The analysis has had all PII (names, SSNs, salaries, etc.) removed for privacy.

Your job is to:
1. Synthesize this analysis into a clear, professional response
2. Improve the structure and clarity
3. Add any relevant HCM best practices or insights
4. Format the response nicely for the user

Do NOT ask for specific names or personal data - work with the sanitized placeholders provided."""

            claude_user_prompt = f"""The user asked: "{query}"

A local AI has analyzed the customer's documents and provided this SANITIZED analysis:

{sanitized_response}

Please synthesize this into a clear, professional response for the user. 
Maintain the sanitized placeholders (like [Employee A], [AMOUNT REDACTED], etc.) - do not try to guess the actual values."""

            claude_response, claude_success = self._call_claude(
                claude_user_prompt,
                claude_system_prompt
            )
            
            result["models_used"].append("claude-sonnet")
            
            if claude_success:
                result["response"] = claude_response
            else:
                # Fall back to sanitized local response
                logger.warning("Claude failed, using sanitized local response")
                result["response"] = sanitized_response
        else:
            # No Claude - use sanitized local response
            result["response"] = sanitized_response
        
        return result
    
    def check_models_available(self) -> Dict[str, bool]:
        """Check which models are available"""
        status = {
            "mistral": False,
            "deepseek": False,
            "claude": False
        }
        
        # Check Ollama models
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                timeout=10
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                for name in model_names:
                    if "mistral" in name.lower():
                        status["mistral"] = True
                    if "deepseek" in name.lower():
                        status["deepseek"] = True
                        
        except Exception as e:
            logger.error(f"Failed to check Ollama models: {e}")
        
        # Check Claude
        status["claude"] = bool(self.claude_api_key)
        
        return status
