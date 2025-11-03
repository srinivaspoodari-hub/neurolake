"""
Rate Limiting

Implements token bucket algorithm for rate limiting LLM requests.
"""

import time
from typing import Dict
from threading import Lock
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int
    burst_size: int = 10

    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second."""
        return self.requests_per_minute / 60.0


class RateLimiter:
    """
    Token bucket rate limiter.

    Example:
        limiter = RateLimiter(requests_per_minute=60)

        # Wait if needed before making request
        limiter.acquire()
        make_api_call()
    """

    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size
        """
        self.config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            burst_size=burst_size
        )
        self.tokens = float(burst_size)
        self.max_tokens = float(burst_size)
        self.last_update = time.time()
        self.lock = Lock()

    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire
            blocking: Whether to block until tokens are available

        Returns:
            True if acquired, False if not available and non-blocking
        """
        with self.lock:
            while True:
                # Refill tokens based on time passed
                now = time.time()
                time_passed = now - self.last_update
                self.tokens = min(
                    self.max_tokens,
                    self.tokens + time_passed * self.config.tokens_per_second
                )
                self.last_update = now

                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                if not blocking:
                    return False

                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.config.tokens_per_second

                # Release lock while waiting
                self.lock.release()
                time.sleep(min(wait_time, 1.0))
                self.lock.acquire()

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get estimated wait time for tokens.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        with self.lock:
            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.config.tokens_per_second


class MultiProviderRateLimiter:
    """
    Rate limiter that manages limits for multiple providers.

    Example:
        limiter = MultiProviderRateLimiter()
        limiter.set_limit("openai", requests_per_minute=60)
        limiter.set_limit("anthropic", requests_per_minute=50)

        limiter.acquire("openai")
        make_openai_call()
    """

    def __init__(self):
        """Initialize multi-provider rate limiter."""
        self.limiters: Dict[str, RateLimiter] = {}
        self.lock = Lock()

    def set_limit(
        self,
        provider: str,
        requests_per_minute: int,
        burst_size: int = 10
    ):
        """
        Set rate limit for a provider.

        Args:
            provider: Provider name
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size
        """
        with self.lock:
            self.limiters[provider] = RateLimiter(
                requests_per_minute=requests_per_minute,
                burst_size=burst_size
            )

    def acquire(self, provider: str, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens for a provider.

        Args:
            provider: Provider name
            tokens: Number of tokens to acquire
            blocking: Whether to block

        Returns:
            True if acquired, False otherwise
        """
        with self.lock:
            if provider not in self.limiters:
                # No limit set, allow by default
                return True

            limiter = self.limiters[provider]

        # Acquire outside of lock to allow concurrent access
        return limiter.acquire(tokens, blocking)

    def get_wait_time(self, provider: str, tokens: int = 1) -> float:
        """Get estimated wait time for a provider."""
        with self.lock:
            if provider not in self.limiters:
                return 0.0

            return self.limiters[provider].get_wait_time(tokens)


__all__ = ["RateLimiter", "MultiProviderRateLimiter", "RateLimitConfig"]
