"""
Parallel LLM Processing Utility
================================
Shared utility for parallel LLM calls across all XLR8 processors.

Used by:
- Register Extractor (Groq page extraction)
- Smart PDF Analyzer (Ollama analysis)
- Standards Processor (rule extraction)

Key design decisions:
- NO batching of content (avoids stitching problems)
- Each unit of work is processed independently
- Results merged after all calls complete
- Configurable concurrency per LLM provider

Deploy to: backend/utils/parallel_llm.py
"""

import os
import time
import random
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class ParallelConfig:
    """Configuration for parallel LLM processing."""
    max_workers: int = 10           # Max concurrent API calls
    timeout_seconds: int = 90       # Per-call timeout
    max_retries: int = 3            # Retries per failed call
    retry_base_delay: float = 2.0   # Base delay for exponential backoff
    jitter_max: float = 1.0         # Max random jitter added to delays
    
    # Provider-specific defaults
    GROQ_MAX_WORKERS: int = 10      # Groq paid tier handles this easily
    OLLAMA_MAX_WORKERS: int = 3     # Local LLM - limited by GPU
    CLAUDE_MAX_WORKERS: int = 5     # API rate limits


# =============================================================================
# RESULT TYPES
# =============================================================================

@dataclass
class LLMResult:
    """Result from a single LLM call."""
    index: int                      # Original position in batch
    success: bool
    content: str = ""               # Raw response content
    parsed: Any = None              # Parsed result (e.g., JSON)
    error: Optional[str] = None
    latency_ms: int = 0
    retries: int = 0


@dataclass 
class ParallelResult:
    """Aggregated results from parallel processing."""
    results: List[LLMResult]
    total_items: int
    successful: int
    failed: int
    total_time_ms: int
    avg_latency_ms: int
    
    @property
    def success_rate(self) -> float:
        return self.successful / self.total_items if self.total_items > 0 else 0.0
    
    def get_successful_parsed(self) -> List[Any]:
        """Get all successfully parsed results in original order."""
        sorted_results = sorted([r for r in self.results if r.success], key=lambda x: x.index)
        return [r.parsed for r in sorted_results if r.parsed is not None]


# =============================================================================
# GROQ PARALLEL PROCESSOR
# =============================================================================

class GroqParallelProcessor:
    """
    Parallel processor for Groq API calls.
    
    Usage:
        processor = GroqParallelProcessor()
        results = processor.process_pages(
            pages=["page1 text", "page2 text", ...],
            prompt_template="Extract data from: {content}",
            parser=json.loads  # Optional parser for responses
        )
    """
    
    def __init__(self, config: Optional[ParallelConfig] = None):
        self.config = config or ParallelConfig()
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("[PARALLEL-GROQ] No GROQ_API_KEY set")
    
    def _call_groq(
        self,
        index: int,
        prompt: str,
        parser: Optional[Callable] = None,
        max_tokens: int = 8192
    ) -> LLMResult:
        """Make a single Groq API call with retries."""
        start_time = time.time()
        retries = 0
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": max_tokens
                    },
                    timeout=self.config.timeout_seconds
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Parse if parser provided
                    parsed = None
                    if parser and content:
                        try:
                            parsed = parser(content)
                        except Exception as parse_err:
                            logger.warning(f"[PARALLEL-GROQ] Item {index} parse error: {parse_err}")
                    
                    latency = int((time.time() - start_time) * 1000)
                    return LLMResult(
                        index=index,
                        success=True,
                        content=content,
                        parsed=parsed,
                        latency_ms=latency,
                        retries=retries
                    )
                
                elif response.status_code == 429:
                    # Rate limited - exponential backoff with jitter
                    retries += 1
                    wait_time = (self.config.retry_base_delay ** attempt) + random.uniform(0, self.config.jitter_max)
                    logger.warning(f"[PARALLEL-GROQ] Item {index} rate limited, waiting {wait_time:.1f}s (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"[PARALLEL-GROQ] Item {index} error: {last_error}")
                    break  # Don't retry non-429 errors
                    
            except requests.exceptions.Timeout:
                last_error = "Timeout"
                retries += 1
                logger.warning(f"[PARALLEL-GROQ] Item {index} timeout (attempt {attempt + 1})")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[PARALLEL-GROQ] Item {index} exception: {e}")
                break
        
        latency = int((time.time() - start_time) * 1000)
        return LLMResult(
            index=index,
            success=False,
            error=last_error,
            latency_ms=latency,
            retries=retries
        )
    
    def process_items(
        self,
        items: List[str],
        prompt_builder: Callable[[int, str], str],
        parser: Optional[Callable] = None,
        max_tokens: int = 8192,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_workers: Optional[int] = None
    ) -> ParallelResult:
        """
        Process multiple items in parallel.
        
        Args:
            items: List of content items to process
            prompt_builder: Function(index, content) -> prompt string
            parser: Optional function to parse response content
            max_tokens: Max tokens per response
            progress_callback: Optional callback(completed, total, message)
            max_workers: Override default max workers
        
        Returns:
            ParallelResult with all results
        """
        if not self.api_key:
            logger.error("[PARALLEL-GROQ] No API key configured")
            return ParallelResult(
                results=[],
                total_items=len(items),
                successful=0,
                failed=len(items),
                total_time_ms=0,
                avg_latency_ms=0
            )
        
        workers = max_workers or min(self.config.GROQ_MAX_WORKERS, len(items))
        logger.warning(f"[PARALLEL-GROQ] Processing {len(items)} items with {workers} workers")
        
        start_time = time.time()
        results: List[LLMResult] = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            futures = {}
            for idx, content in enumerate(items):
                prompt = prompt_builder(idx, content)
                future = executor.submit(self._call_groq, idx, prompt, parser, max_tokens)
                futures[future] = idx
            
            # Collect results as they complete
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                
                if progress_callback:
                    status = "✓" if result.success else "✗"
                    progress_callback(completed, len(items), f"Item {result.index + 1} {status}")
                
                if completed % 10 == 0 or completed == len(items):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    logger.warning(f"[PARALLEL-GROQ] Progress: {completed}/{len(items)} ({rate:.1f}/sec)")
        
        total_time = int((time.time() - start_time) * 1000)
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        avg_latency = sum(r.latency_ms for r in results) // len(results) if results else 0
        
        logger.warning(f"[PARALLEL-GROQ] Complete: {successful}/{len(items)} successful in {total_time}ms")
        
        return ParallelResult(
            results=results,
            total_items=len(items),
            successful=successful,
            failed=failed,
            total_time_ms=total_time,
            avg_latency_ms=avg_latency
        )


# =============================================================================
# OLLAMA PARALLEL PROCESSOR  
# =============================================================================

class OllamaParallelProcessor:
    """
    Parallel processor for local Ollama API calls.
    
    Lower concurrency than Groq since it's limited by local GPU.
    """
    
    def __init__(self, config: Optional[ParallelConfig] = None):
        self.config = config or ParallelConfig()
        self.endpoint = os.getenv("LLM_ENDPOINT", "").rstrip('/')
        self.username = os.getenv("LLM_USERNAME", "")
        self.password = os.getenv("LLM_PASSWORD", "")
        self.model = os.getenv("LLM_MODEL", "mistral:7b")
        
        self.auth = HTTPBasicAuth(self.username, self.password) if self.username else None
        
        if not self.endpoint:
            logger.warning("[PARALLEL-OLLAMA] No LLM_ENDPOINT set")
    
    def _call_ollama(
        self,
        index: int,
        prompt: str,
        parser: Optional[Callable] = None,
        model: Optional[str] = None
    ) -> LLMResult:
        """Make a single Ollama API call with retries."""
        start_time = time.time()
        retries = 0
        last_error = None
        use_model = model or self.model
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    f"{self.endpoint}/api/generate",
                    auth=self.auth,
                    json={
                        "model": use_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 4096
                        }
                    },
                    timeout=self.config.timeout_seconds
                )
                
                if response.status_code == 200:
                    content = response.json().get("response", "")
                    
                    parsed = None
                    if parser and content:
                        try:
                            parsed = parser(content)
                        except Exception as parse_err:
                            logger.warning(f"[PARALLEL-OLLAMA] Item {index} parse error: {parse_err}")
                    
                    latency = int((time.time() - start_time) * 1000)
                    return LLMResult(
                        index=index,
                        success=True,
                        content=content,
                        parsed=parsed,
                        latency_ms=latency,
                        retries=retries
                    )
                
                else:
                    last_error = f"HTTP {response.status_code}"
                    retries += 1
                    time.sleep(self.config.retry_base_delay)
                    
            except requests.exceptions.Timeout:
                last_error = "Timeout"
                retries += 1
                logger.warning(f"[PARALLEL-OLLAMA] Item {index} timeout")
                
            except Exception as e:
                last_error = str(e)
                break
        
        latency = int((time.time() - start_time) * 1000)
        return LLMResult(
            index=index,
            success=False,
            error=last_error,
            latency_ms=latency,
            retries=retries
        )
    
    def process_items(
        self,
        items: List[str],
        prompt_builder: Callable[[int, str], str],
        parser: Optional[Callable] = None,
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_workers: Optional[int] = None
    ) -> ParallelResult:
        """Process multiple items in parallel using Ollama."""
        if not self.endpoint:
            logger.error("[PARALLEL-OLLAMA] No endpoint configured")
            return ParallelResult(
                results=[],
                total_items=len(items),
                successful=0,
                failed=len(items),
                total_time_ms=0,
                avg_latency_ms=0
            )
        
        # Lower concurrency for local LLM
        workers = max_workers or min(self.config.OLLAMA_MAX_WORKERS, len(items))
        logger.warning(f"[PARALLEL-OLLAMA] Processing {len(items)} items with {workers} workers")
        
        start_time = time.time()
        results: List[LLMResult] = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for idx, content in enumerate(items):
                prompt = prompt_builder(idx, content)
                future = executor.submit(self._call_ollama, idx, prompt, parser, model)
                futures[future] = idx
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                
                if progress_callback:
                    status = "✓" if result.success else "✗"
                    progress_callback(completed, len(items), f"Item {result.index + 1} {status}")
        
        total_time = int((time.time() - start_time) * 1000)
        successful = sum(1 for r in results if r.success)
        
        logger.warning(f"[PARALLEL-OLLAMA] Complete: {successful}/{len(items)} in {total_time}ms")
        
        return ParallelResult(
            results=results,
            total_items=len(items),
            successful=successful,
            failed=len(items) - successful,
            total_time_ms=total_time,
            avg_latency_ms=sum(r.latency_ms for r in results) // len(results) if results else 0
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parallel_groq_process(
    items: List[str],
    prompt_builder: Callable[[int, str], str],
    parser: Optional[Callable] = None,
    max_workers: int = 10,
    progress_callback: Optional[Callable] = None
) -> ParallelResult:
    """
    Convenience function for parallel Groq processing.
    
    Example:
        results = parallel_groq_process(
            items=pages,
            prompt_builder=lambda i, text: f"Extract from page {i+1}:\\n{text}",
            parser=parse_json_response,
            max_workers=10
        )
        
        all_employees = []
        for parsed in results.get_successful_parsed():
            all_employees.extend(parsed)
    """
    processor = GroqParallelProcessor()
    return processor.process_items(
        items=items,
        prompt_builder=prompt_builder,
        parser=parser,
        max_workers=max_workers,
        progress_callback=progress_callback
    )


def parallel_ollama_process(
    items: List[str],
    prompt_builder: Callable[[int, str], str],
    parser: Optional[Callable] = None,
    model: str = None,
    max_workers: int = 3,
    progress_callback: Optional[Callable] = None
) -> ParallelResult:
    """Convenience function for parallel Ollama processing."""
    processor = OllamaParallelProcessor()
    return processor.process_items(
        items=items,
        prompt_builder=prompt_builder,
        parser=parser,
        model=model,
        max_workers=max_workers,
        progress_callback=progress_callback
    )
