"""
LLM Caller - Unified Interface for Multiple LLM Backends

Provides a clean abstraction for calling:
- Ollama (local models: Mistral, DeepSeek)
- Claude API (for general knowledge)

Handles errors, timeouts, retries, and streaming responses.

Author: HCMPACT
Version: 1.0
"""

import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Tuple, Dict, Any, Generator
import logging
import time
import json

logger = logging.getLogger(__name__)


class LLMCallerError(Exception):
    """Base exception for LLM caller errors"""
    pass


class OllamaError(LLMCallerError):
    """Ollama-specific errors"""
    pass


class ClaudeAPIError(LLMCallerError):
    """Claude API-specific errors"""
    pass


class LLMCaller:
    """
    Unified interface for calling different LLM backends.
    
    Supports:
    - Ollama (Mistral, DeepSeek, etc.)
    - Claude API (Sonnet 4)
    """
    
    def __init__(self, 
                 ollama_endpoint: str,
                 ollama_auth: Optional[Tuple[str, str]] = None,
                 claude_api_key: Optional[str] = None,
                 default_timeout: int = 120):
        """
        Initialize LLM caller.
        
        Args:
            ollama_endpoint: Ollama server URL (e.g., http://178.156.190.64:11435)
            ollama_auth: Optional (username, password) tuple for Ollama
            claude_api_key: Optional Claude API key
            default_timeout: Default timeout in seconds
        """
        self.ollama_endpoint = ollama_endpoint.rstrip('/')
        self.ollama_auth = ollama_auth
        self.claude_api_key = claude_api_key
        self.default_timeout = default_timeout
        
        logger.info(f"LLM Caller initialized - Ollama: {self.ollama_endpoint}, Claude: {'Yes' if claude_api_key else 'No'}")
    
    def call_ollama(self,
                    prompt: str,
                    model: str = "mistral:7b",
                    system_prompt: Optional[str] = None,
                    temperature: float = 0.7,
                    max_tokens: int = 4096,
                    stream: bool = False,
                    timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Call Ollama API for local LLM inference.
        
        Args:
            prompt: User prompt
            model: Model name (e.g., "mistral:7b", "deepseek-r1:7b")
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            timeout: Request timeout in seconds
            
        Returns:
            Dict with 'response' (full text) and 'metadata' (timing, tokens, etc.)
            
        Raises:
            OllamaError: If the request fails
        """
        url = f"{self.ollama_endpoint}/api/generate"
        timeout = timeout or self.default_timeout
        
        # Build request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        logger.info(f"Calling Ollama - Model: {model}, Stream: {stream}")
        start_time = time.time()
        
        try:
            # Make request
            auth = HTTPBasicAuth(*self.ollama_auth) if self.ollama_auth else None
            
            if stream:
                # Streaming response
                response = requests.post(
                    url,
                    json=payload,
                    auth=auth,
                    timeout=timeout,
                    stream=True
                )
                response.raise_for_status()
                
                return {
                    'stream': self._stream_ollama_response(response),
                    'model': model,
                    'started_at': start_time
                }
            else:
                # Non-streaming response
                response = requests.post(
                    url,
                    json=payload,
                    auth=auth,
                    timeout=timeout
                )
                response.raise_for_status()
                
                data = response.json()
                elapsed = time.time() - start_time
                
                logger.info(f"Ollama response received in {elapsed:.2f}s")
                
                return {
                    'response': data.get('response', ''),
                    'metadata': {
                        'model': model,
                        'elapsed_seconds': elapsed,
                        'total_duration': data.get('total_duration', 0),
                        'load_duration': data.get('load_duration', 0),
                        'prompt_eval_count': data.get('prompt_eval_count', 0),
                        'eval_count': data.get('eval_count', 0)
                    }
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {timeout}s")
            raise OllamaError(f"Request timed out after {timeout} seconds")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Ollama at {self.ollama_endpoint}: {e}")
            raise OllamaError(f"Cannot connect to Ollama server: {str(e)}")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', str(e))
            except:
                error_msg = str(e)
            raise OllamaError(f"Ollama API error: {error_msg}")
            
        except Exception as e:
            logger.error(f"Unexpected Ollama error: {e}")
            raise OllamaError(f"Unexpected error: {str(e)}")
    
    def _stream_ollama_response(self, response) -> Generator[str, None, None]:
        """
        Stream Ollama response chunks.
        
        Args:
            response: Requests response object with stream=True
            
        Yields:
            Response text chunks
        """
        try:
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            yield data['response']
                        
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"Could not decode streaming line: {line}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error streaming Ollama response: {e}")
            raise OllamaError(f"Streaming error: {str(e)}")
    
    def call_claude_api(self,
                       prompt: str,
                       system_prompt: Optional[str] = None,
                       max_tokens: int = 4096,
                       temperature: float = 0.7,
                       timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Call Claude API for general knowledge queries.
        
        IMPORTANT: Only call this for queries WITHOUT PII!
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            timeout: Request timeout in seconds
            
        Returns:
            Dict with 'response' (full text) and 'metadata'
            
        Raises:
            ClaudeAPIError: If the request fails
        """
        if not self.claude_api_key:
            raise ClaudeAPIError("Claude API key not configured")
        
        url = "https://api.anthropic.com/v1/messages"
        timeout = timeout or self.default_timeout
        
        # Build request payload
        headers = {
            "x-api-key": self.claude_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        logger.info("Calling Claude API")
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            elapsed = time.time() - start_time
            
            # Extract response text
            response_text = ""
            if "content" in data and len(data["content"]) > 0:
                response_text = data["content"][0].get("text", "")
            
            logger.info(f"Claude API response received in {elapsed:.2f}s")
            
            return {
                'response': response_text,
                'metadata': {
                    'model': 'claude-sonnet-4-20250514',
                    'elapsed_seconds': elapsed,
                    'input_tokens': data.get('usage', {}).get('input_tokens', 0),
                    'output_tokens': data.get('usage', {}).get('output_tokens', 0),
                    'stop_reason': data.get('stop_reason', 'unknown')
                }
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Claude API request timed out after {timeout}s")
            raise ClaudeAPIError(f"Request timed out after {timeout} seconds")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Claude API: {e}")
            raise ClaudeAPIError(f"Cannot connect to Claude API: {str(e)}")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Claude API HTTP error: {e}")
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', str(e))
            except:
                error_msg = str(e)
            raise ClaudeAPIError(f"Claude API error: {error_msg}")
            
        except Exception as e:
            logger.error(f"Unexpected Claude API error: {e}")
            raise ClaudeAPIError(f"Unexpected error: {str(e)}")
    
    def call_with_retry(self,
                       use_local: bool,
                       prompt: str,
                       model: Optional[str] = None,
                       max_retries: int = 3,
                       **kwargs) -> Dict[str, Any]:
        """
        Call LLM with automatic retry logic.
        
        Args:
            use_local: True for Ollama, False for Claude API
            prompt: User prompt
            model: Model name (for Ollama)
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments passed to the LLM caller
            
        Returns:
            LLM response dict
            
        Raises:
            LLMCallerError: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if use_local:
                    if not model:
                        model = "mistral:7b"
                    return self.call_ollama(prompt, model=model, **kwargs)
                else:
                    return self.call_claude_api(prompt, **kwargs)
                    
            except (OllamaError, ClaudeAPIError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        # All retries failed
        raise LLMCallerError(f"Failed after {max_retries} attempts: {last_error}")


# Convenience functions
def call_ollama(prompt: str,
                endpoint: str,
                model: str = "mistral:7b",
                auth: Optional[Tuple[str, str]] = None,
                **kwargs) -> Dict[str, Any]:
    """
    Convenience function to call Ollama.
    
    Args:
        prompt: User prompt
        endpoint: Ollama server URL
        model: Model name
        auth: Optional (username, password) tuple
        **kwargs: Additional arguments
        
    Returns:
        Response dict
    """
    caller = LLMCaller(ollama_endpoint=endpoint, ollama_auth=auth)
    return caller.call_ollama(prompt, model=model, **kwargs)


def call_claude_api(prompt: str,
                   api_key: str,
                   **kwargs) -> Dict[str, Any]:
    """
    Convenience function to call Claude API.
    
    Args:
        prompt: User prompt
        api_key: Claude API key
        **kwargs: Additional arguments
        
    Returns:
        Response dict
    """
    caller = LLMCaller(ollama_endpoint="", claude_api_key=api_key)
    return caller.call_claude_api(prompt, **kwargs)
