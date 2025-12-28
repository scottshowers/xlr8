"""
Retry Utilities for External API Calls
======================================

Provides retry decorators and helpers for resilient external API calls.

Usage:
    from utils.retry_utils import retry_async, retry_sync, HttpxClientWithRetry

    # Decorator for async functions
    @retry_async(max_attempts=3, backoff_base=2.0)
    async def call_external_api():
        ...

    # Decorator for sync functions  
    @retry_sync(max_attempts=3, backoff_base=2.0)
    def call_external_api():
        ...

    # Pre-configured httpx client with retry
    async with HttpxClientWithRetry() as client:
        response = await client.post(url, json=data)

Author: XLR8 Team
Version: 1.0.0 - Week 3 Hardening
"""

import asyncio
import time
import random
import logging
import functools
from typing import Optional, Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)

# Exceptions that should trigger retry
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,  # Includes network errors
)

# HTTP status codes that should trigger retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def retry_async(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    jitter_max: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    retryable_status_codes: set = RETRYABLE_STATUS_CODES,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Async retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first try)
        backoff_base: Base for exponential backoff (delay = base^attempt)
        jitter_max: Maximum random jitter to add to delay
        retryable_exceptions: Tuple of exception types that trigger retry
        retryable_status_codes: Set of HTTP status codes that trigger retry
        on_retry: Optional callback(attempt, exception) called before each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Check for retryable HTTP status if result has status_code
                    if hasattr(result, 'status_code'):
                        if result.status_code in retryable_status_codes:
                            if attempt < max_attempts - 1:
                                delay = (backoff_base ** attempt) + random.uniform(0, jitter_max)
                                logger.warning(
                                    f"[RETRY] {func.__name__} got HTTP {result.status_code}, "
                                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})"
                                )
                                await asyncio.sleep(delay)
                                continue
                    
                    return result
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        delay = (backoff_base ** attempt) + random.uniform(0, jitter_max)
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        logger.warning(
                            f"[RETRY] {func.__name__} failed with {type(e).__name__}: {e}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                        
            # If we exhausted retries due to status codes
            if last_exception:
                raise last_exception
            return result
            
        return wrapper
    return decorator


def retry_sync(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    jitter_max: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Sync retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first try)
        backoff_base: Base for exponential backoff (delay = base^attempt)
        jitter_max: Maximum random jitter to add to delay
        retryable_exceptions: Tuple of exception types that trigger retry
        on_retry: Optional callback(attempt, exception) called before each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        delay = (backoff_base ** attempt) + random.uniform(0, jitter_max)
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        logger.warning(
                            f"[RETRY] {func.__name__} failed with {type(e).__name__}: {e}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                        
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


# =============================================================================
# HTTPX CLIENT WITH BUILT-IN RETRY
# =============================================================================

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


if HTTPX_AVAILABLE:
    class HttpxClientWithRetry:
        """
        Async httpx client wrapper with automatic retry for transient failures.
        
        Usage:
            async with HttpxClientWithRetry(timeout=30, max_retries=3) as client:
                response = await client.get("https://api.example.com/data")
        """
        
        def __init__(
            self,
            timeout: float = 30.0,
            max_retries: int = 3,
            backoff_base: float = 2.0,
            **httpx_kwargs
        ):
            self.timeout = timeout
            self.max_retries = max_retries
            self.backoff_base = backoff_base
            self.httpx_kwargs = httpx_kwargs
            self._client: Optional[httpx.AsyncClient] = None
        
        async def __aenter__(self):
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                **self.httpx_kwargs
            )
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._client:
                await self._client.aclose()
        
        async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
            """Make request with automatic retry on transient failures."""
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    response = await getattr(self._client, method)(url, **kwargs)
                    
                    # Retry on server errors and rate limits
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < self.max_retries - 1:
                            delay = (self.backoff_base ** attempt) + random.uniform(0, 1)
                            logger.warning(
                                f"[HTTPX-RETRY] {method.upper()} {url} got {response.status_code}, "
                                f"retrying in {delay:.1f}s"
                            )
                            await asyncio.sleep(delay)
                            continue
                    
                    return response
                    
                except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                    last_exception = e
                    
                    if attempt < self.max_retries - 1:
                        delay = (self.backoff_base ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"[HTTPX-RETRY] {method.upper()} {url} failed: {e}, "
                            f"retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[HTTPX-RETRY] {method.upper()} {url} failed after {self.max_retries} attempts")
                        raise
            
            if last_exception:
                raise last_exception
            return response
        
        async def get(self, url: str, **kwargs) -> httpx.Response:
            return await self._request_with_retry("get", url, **kwargs)
        
        async def post(self, url: str, **kwargs) -> httpx.Response:
            return await self._request_with_retry("post", url, **kwargs)
        
        async def put(self, url: str, **kwargs) -> httpx.Response:
            return await self._request_with_retry("put", url, **kwargs)
        
        async def delete(self, url: str, **kwargs) -> httpx.Response:
            return await self._request_with_retry("delete", url, **kwargs)
        
        async def patch(self, url: str, **kwargs) -> httpx.Response:
            return await self._request_with_retry("patch", url, **kwargs)


# =============================================================================
# REQUESTS (SYNC) WRAPPER
# =============================================================================

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def requests_with_retry(
    method: str,
    url: str,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    timeout: float = 30.0,
    **kwargs
) -> 'requests.Response':
    """
    Make a requests call with automatic retry.
    
    Usage:
        response = requests_with_retry("get", "https://api.example.com/data")
        response = requests_with_retry("post", url, json={"key": "value"})
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library not available")
    
    kwargs.setdefault('timeout', timeout)
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = getattr(requests, method)(url, **kwargs)
            
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < max_retries - 1:
                    delay = (backoff_base ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"[REQUESTS-RETRY] {method.upper()} {url} got {response.status_code}, "
                        f"retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    continue
            
            return response
            
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                delay = (backoff_base ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"[REQUESTS-RETRY] {method.upper()} {url} failed: {e}, "
                    f"retrying in {delay:.1f}s"
                )
                time.sleep(delay)
            else:
                logger.error(f"[REQUESTS-RETRY] {method.upper()} {url} failed after {max_retries} attempts")
                raise
    
    if last_exception:
        raise last_exception
    return response
