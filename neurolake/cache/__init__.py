"""
NeuroLake Query Cache

Query result caching with Redis backend, LRU eviction, and metrics tracking.

Example:
    from neurolake.cache import QueryCache

    cache = QueryCache(host="localhost", port=6379)

    # Check cache
    result = cache.get(sql)
    if result is None:
        result = execute_query(sql)
        cache.put(sql, result, ttl=3600)
"""

from neurolake.cache.cache import QueryCache
from neurolake.cache.key_generator import CacheKeyGenerator
from neurolake.cache.metrics import CacheMetrics, CacheMetricsCollector

__all__ = [
    "QueryCache",
    "CacheKeyGenerator",
    "CacheMetrics",
    "CacheMetricsCollector",
]
