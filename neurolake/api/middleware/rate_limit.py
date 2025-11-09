"""
Rate Limiting Middleware

Token bucket algorithm for rate limiting API requests.
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class TokenBucket:
    """
    Token bucket for rate limiting.

    Args:
        capacity: Maximum number of tokens
        refill_rate: Tokens added per second
    """

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_wait_time(self) -> float:
        """Get time to wait until a token is available."""
        if self.tokens >= 1:
            return 0.0
        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Args:
        requests_per_minute: Maximum requests per minute per client
        burst_size: Maximum burst size (defaults to requests_per_minute)
    """

    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second

        # Client buckets: {client_id: TokenBucket}
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.burst_size, self.refill_rate)
        )

        # Cleanup old buckets periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier.

        Uses X-Forwarded-For if available, otherwise client IP.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_old_buckets(self):
        """Remove inactive buckets to prevent memory leak."""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            # Remove buckets that have been full for a while (inactive clients)
            inactive_threshold = 3600  # 1 hour
            to_remove = []

            for client_id, bucket in self.buckets.items():
                if (bucket.tokens >= bucket.capacity and
                    now - bucket.last_refill > inactive_threshold):
                    to_remove.append(client_id)

            for client_id in to_remove:
                del self.buckets[client_id]

            self.last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Get or create bucket for this client
        bucket = self.buckets[client_id]

        # Try to consume a token
        if not bucket.consume():
            wait_time = bucket.get_wait_time()

            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {wait_time:.1f} seconds.",
                    "retry_after": int(wait_time) + 1,
                    "limit": self.requests_per_minute,
                    "window": "60s"
                },
                headers={
                    "Retry-After": str(int(wait_time) + 1),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + wait_time))
                }
            )

        # Process request
        response: Response = await call_next(request)

        # Add rate limit headers
        remaining = int(bucket.tokens)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        # Periodic cleanup
        self._cleanup_old_buckets()

        return response
