"""
LLM Response Caching

Cache LLM responses to reduce costs and latency.
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """Cached LLM response."""
    key: str
    response: Dict[str, Any]
    timestamp: float
    ttl: int  # Time to live in seconds
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl == 0:
            return False  # Never expires
        return (time.time() - self.timestamp) > self.ttl


class LLMCache:
    """
    In-memory cache for LLM responses.

    Example:
        cache = LLMCache(ttl=3600)  # 1 hour TTL

        # Check cache
        key = cache.generate_key("What is a data lake?", model="gpt-4")
        if cached := cache.get(key):
            return cached

        # Make API call and cache
        response = call_llm()
        cache.set(key, response)
    """

    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        Initialize cache.

        Args:
            ttl: Time to live in seconds (0 = never expires)
            max_size: Maximum number of entries
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def generate_key(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            prompt: The prompt
            model: Model name
            temperature: Temperature
            max_tokens: Max tokens
            **kwargs: Additional parameters

        Returns:
            Cache key (SHA256 hash)
        """
        # Create deterministic key from parameters
        key_data = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        # Sort keys for deterministic hashing
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()

        return key_hash

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response.

        Args:
            key: Cache key

        Returns:
            Cached response or None
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Check if expired
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        # Update hit count
        entry.hits += 1
        self.hits += 1

        return entry.response

    def set(self, key: str, response: Dict[str, Any], ttl: Optional[int] = None):
        """
        Cache a response.

        Args:
            key: Cache key
            response: Response to cache
            ttl: Optional TTL override
        """
        # Evict if at max size
        if len(self.cache) >= self.max_size:
            self._evict_lru()

        entry = CacheEntry(
            key=key,
            response=response,
            timestamp=time.time(),
            ttl=ttl if ttl is not None else self.ttl
        )

        self.cache[key] = entry

    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find entry with oldest timestamp and fewest hits
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k].hits, self.cache[k].timestamp)
        )

        del self.cache[lru_key]

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "ttl": self.ttl
        }

    def cleanup_expired(self):
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self.cache[key]

    def save(self, path: Path):
        """Save cache to disk."""
        data = {
            "entries": [
                {
                    "key": entry.key,
                    "response": entry.response,
                    "timestamp": entry.timestamp,
                    "ttl": entry.ttl,
                    "hits": entry.hits
                }
                for entry in self.cache.values()
            ],
            "stats": self.get_stats()
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path):
        """Load cache from disk."""
        with open(path, "r") as f:
            data = json.load(f)

        self.cache.clear()

        for entry_data in data.get("entries", []):
            entry = CacheEntry(**entry_data)
            if not entry.is_expired():
                self.cache[entry.key] = entry


__all__ = ["LLMCache", "CacheEntry"]
