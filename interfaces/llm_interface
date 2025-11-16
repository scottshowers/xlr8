"""
LLM Interface Contract
All LLM implementations MUST follow this interface

Allows swapping between Local LLM, Claude, GPT, etc. without code changes.
"""

from typing import Protocol, List, Dict, Any, Optional, Iterator
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""
    LOCAL = "local"          # Local Ollama
    CLAUDE = "claude"        # Anthropic Claude
    OPENAI = "openai"        # OpenAI GPT
    CUSTOM = "custom"        # Custom implementation


class LLMInterface(Protocol):
    """
    Interface contract for LLM providers.
    
    Any LLM implementation must follow this interface to be compatible
    with Chat and Analysis modules.
    
    Team members can add new LLM providers as long as they follow this contract.
    """
    
    def generate(self,
                prompt: str,
                max_tokens: int = 1000,
                temperature: float = 0.7,
                stream: bool = False) -> Dict[str, Any]:
        """
        Generate LLM response (non-streaming).
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            stream: Whether to stream response
        
        Returns:
            {
                'text': str,              # Generated text
                'tokens_used': int,       # Total tokens consumed
                'finish_reason': str,     # 'stop', 'length', 'error'
                'model': str,             # Model used
                'provider': str,          # Provider name
                'cost_usd': float,        # Estimated cost (0.0 for local)
                'latency_ms': float,      # Response time
                'success': bool,
                'error': Optional[str]
            }
        
        Example:
            result = llm.generate(
                prompt="Explain UKG earnings configuration",
                max_tokens=500
            )
            if result['success']:
                print(result['text'])
        """
        ...
    
    def generate_stream(self,
                       prompt: str,
                       max_tokens: int = 1000,
                       temperature: float = 0.7) -> Iterator[str]:
        """
        Generate LLM response with streaming.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
        
        Yields:
            str: Token chunks as they're generated
        
        Example:
            for token in llm.generate_stream(prompt="Hello"):
                print(token, end='', flush=True)
        """
        ...
    
    def chat(self,
            messages: List[Dict[str, str]],
            max_tokens: int = 1000,
            temperature: float = 0.7,
            stream: bool = False) -> Dict[str, Any]:
        """
        Chat completion with message history.
        
        Args:
            messages: List of message dicts
                     [
                         {'role': 'user', 'content': 'Hello'},
                         {'role': 'assistant', 'content': 'Hi!'},
                         {'role': 'user', 'content': 'How are you?'}
                     ]
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream
        
        Returns:
            Same format as generate()
        
        Example:
            messages = [
                {'role': 'user', 'content': 'What is UKG?'}
            ]
            result = llm.chat(messages)
        """
        ...
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the LLM model.
        
        Returns:
            {
                'provider': str,          # e.g., "local", "claude"
                'model_name': str,        # e.g., "deepseek-r1:7b"
                'context_window': int,    # Max context tokens
                'max_output': int,        # Max output tokens
                'cost_per_1k_input': float,   # USD cost
                'cost_per_1k_output': float,  # USD cost
                'capabilities': List[str] # e.g., ["chat", "streaming"]
            }
        
        Example:
            info = llm.get_model_info()
            print(f"Using {info['model_name']}")
        """
        ...
    
    def validate_connection(self) -> Dict[str, Any]:
        """
        Validate LLM connection.
        
        Returns:
            {
                'connected': bool,
                'latency_ms': float,
                'model_available': bool,
                'error': Optional[str]
            }
        
        Example:
            status = llm.validate_connection()
            if status['connected']:
                print("✅ LLM Ready")
        """
        ...
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Input text
        
        Returns:
            Estimated token count
        
        Example:
            tokens = llm.estimate_tokens("Hello world")
            # Returns: ~2
        """
        ...
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            Estimated cost in USD
        
        Example:
            cost = llm.estimate_cost(100, 50)
            # Returns: 0.0015 (for Claude)
        """
        ...


class StreamingLLMInterface(Protocol):
    """
    Enhanced interface for streaming LLM responses.
    
    Provides better control over streaming behavior.
    """
    
    def stream_with_metadata(self,
                            prompt: str,
                            max_tokens: int = 1000,
                            temperature: float = 0.7) -> Iterator[Dict[str, Any]]:
        """
        Stream response with metadata for each chunk.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
        
        Yields:
            {
                'token': str,            # Token text
                'cumulative': str,       # Full text so far
                'tokens_used': int,      # Tokens used so far
                'is_final': bool,        # Last chunk?
                'metadata': dict         # Additional info
            }
        
        Example:
            for chunk in llm.stream_with_metadata(prompt):
                print(chunk['token'], end='')
                if chunk['is_final']:
                    print(f"\nUsed {chunk['tokens_used']} tokens")
        """
        ...


# Example implementations
class LocalLLMExample:
    """
    Example local LLM implementation (Ollama).
    
    Template for team members.
    """
    
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model
        self.provider = LLMProvider.LOCAL
    
    def generate(self, prompt: str, max_tokens: int = 1000,
                temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """Example implementation"""
        import requests
        import time
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            
            latency = (time.time() - start_time) * 1000
            
            return {
                'text': result.get('response', ''),
                'tokens_used': result.get('eval_count', 0),
                'finish_reason': 'stop',
                'model': self.model,
                'provider': 'local',
                'cost_usd': 0.0,  # Local is free
                'latency_ms': latency,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'text': '',
                'tokens_used': 0,
                'finish_reason': 'error',
                'model': self.model,
                'provider': 'local',
                'cost_usd': 0.0,
                'latency_ms': 0.0,
                'success': False,
                'error': str(e)
            }
    
    def generate_stream(self, prompt: str, max_tokens: int = 1000,
                       temperature: float = 0.7) -> Iterator[str]:
        """Example streaming implementation"""
        import requests
        
        response = requests.post(
            f"{self.endpoint}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                import json
                try:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        yield chunk['response']
                except json.JSONDecodeError:
                    continue
    
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000,
            temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """Convert messages to prompt and call generate"""
        # Build prompt from messages
        prompt = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages
        ])
        return self.generate(prompt, max_tokens, temperature, stream)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Example model info"""
        return {
            'provider': 'local',
            'model_name': self.model,
            'context_window': 8192,
            'max_output': 4096,
            'cost_per_1k_input': 0.0,
            'cost_per_1k_output': 0.0,
            'capabilities': ['chat', 'streaming', 'completion']
        }
    
    def validate_connection(self) -> Dict[str, Any]:
        """Example connection validation"""
        import requests
        import time
        
        try:
            start = time.time()
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            latency = (time.time() - start) * 1000
            
            return {
                'connected': response.status_code == 200,
                'latency_ms': latency,
                'model_available': True,
                'error': None
            }
        except Exception as e:
            return {
                'connected': False,
                'latency_ms': 0.0,
                'model_available': False,
                'error': str(e)
            }
    
    def estimate_tokens(self, text: str) -> int:
        """Simple token estimation"""
        # Rough estimate: ~4 chars per token
        return len(text) // 4
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Local LLM is free"""
        return 0.0


class ClaudeLLMExample:
    """
    Example Claude API implementation.
    
    Template for team members.
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.provider = LLMProvider.CLAUDE
    
    def generate(self, prompt: str, max_tokens: int = 1000,
                temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """Example Claude implementation"""
        import anthropic
        import time
        
        start_time = time.time()
        
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            latency = (time.time() - start_time) * 1000
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            
            return {
                'text': message.content[0].text,
                'tokens_used': input_tokens + output_tokens,
                'finish_reason': message.stop_reason,
                'model': self.model,
                'provider': 'claude',
                'cost_usd': self.estimate_cost(input_tokens, output_tokens),
                'latency_ms': latency,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'text': '',
                'tokens_used': 0,
                'finish_reason': 'error',
                'model': self.model,
                'provider': 'claude',
                'cost_usd': 0.0,
                'latency_ms': 0.0,
                'success': False,
                'error': str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Claude model info"""
        return {
            'provider': 'claude',
            'model_name': self.model,
            'context_window': 200000,
            'max_output': 8192,
            'cost_per_1k_input': 0.003,
            'cost_per_1k_output': 0.015,
            'capabilities': ['chat', 'streaming', 'completion']
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate Claude API cost"""
        input_cost = (input_tokens / 1000) * 0.003
        output_cost = (output_tokens / 1000) * 0.015
        return input_cost + output_cost
    
    # ... other methods similar to LocalLLMExample
