"""
Query Cache

Redis-based query result caching with LRU eviction, TTL, and metrics.
"""

import json
import logging
import pickle
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from neurolake.cache.key_generator import CacheKeyGenerator
from neurolake.cache.metrics import CacheMetrics, CacheMetricsCollector


logger = logging.getLogger(__name__)


class QueryCache:
    """
    Query result cache with Redis backend and LRU eviction.

    Features:
    - Redis backend with fallback to in-memory cache
    - Configurable TTL (time-to-live)
    - LRU eviction policy
    - Size limits (max keys and max memory)
    - Hit/miss metrics tracking
    - Cache invalidation by table or pattern

    Example:
        # With Redis
        cache = QueryCache(
            host="localhost",
            port=6379,
            default_ttl=3600,
            max_keys=10000,
        )

        # Check cache
        result = cache.get("SELECT * FROM users")
        if result is None:
            result = execute_query("SELECT * FROM users")
            cache.put("SELECT * FROM users", result)

        # Get metrics
        metrics = cache.get_metrics()
        print(f"Hit rate: {metrics.hit_rate:.2%}")

        # Invalidate
        cache.invalidate_table("users")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,
        max_keys: Optional[int] = None,
        max_memory_mb: Optional[int] = None,
        use_redis: bool = True,
        key_prefix: str = "neurolake",
        track_metrics: bool = True,
    ):
        """
        Initialize query cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            default_ttl: Default TTL in seconds (0 = no expiration)
            max_keys: Maximum number of cached keys (None = unlimited)
            max_memory_mb: Maximum memory usage in MB (None = unlimited)
            use_redis: Use Redis if available (fallback to in-memory)
            key_prefix: Cache key prefix
            track_metrics: Enable metrics tracking
        """
        self.default_ttl = default_ttl
        self.max_keys = max_keys
        self.max_memory_bytes = max_memory_mb * 1024 * 1024 if max_memory_mb else None
        self.track_metrics = track_metrics

        # Initialize key generator
        self.key_generator = CacheKeyGenerator(prefix=key_prefix)

        # Initialize metrics collector
        self.metrics_collector = (
            CacheMetricsCollector() if track_metrics else None
        )

        # Redis client
        self.redis_client: Optional[redis.Redis] = None
        self.use_redis = use_redis and REDIS_AVAILABLE

        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=False,  # We'll handle encoding
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis at {host}:{port}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
                self.redis_client = None
                self.use_redis = False

        # In-memory cache (fallback or if Redis not available)
        if not self.use_redis:
            logger.info("Using in-memory LRU cache")
            self.memory_cache: OrderedDict = OrderedDict()
            self.memory_size_bytes = 0

        # Table -> keys mapping for invalidation
        self.table_keys_map: Dict[str, set] = {}

    def get(
        self,
        sql: str,
        params: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Get cached query result.

        Args:
            sql: SQL query string
            params: Query parameters
            metadata: Optional metadata for cache key

        Returns:
            Cached result or None if not found
        """
        start_time = time.time()

        try:
            # Generate cache key
            cache_key = self.key_generator.generate(sql, params, metadata)

            # Get from cache
            if self.use_redis and self.redis_client:
                result = self._redis_get(cache_key)
            else:
                result = self._memory_get(cache_key)

            # Record metrics
            elapsed_ms = (time.time() - start_time) * 1000
            if result is not None:
                if self.metrics_collector:
                    self.metrics_collector.record_hit(get_time_ms=elapsed_ms)
                logger.debug(f"Cache HIT: {cache_key[:16]}... ({elapsed_ms:.2f}ms)")
                return result
            else:
                if self.metrics_collector:
                    self.metrics_collector.record_miss(get_time_ms=elapsed_ms)
                logger.debug(f"Cache MISS: {cache_key[:16]}... ({elapsed_ms:.2f}ms)")
                return None

        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            if self.metrics_collector:
                self.metrics_collector.record_error()
            return None

    def put(
        self,
        sql: str,
        result: Any,
        params: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Put query result into cache.

        Args:
            sql: SQL query string
            result: Query result to cache
            params: Query parameters
            metadata: Optional metadata for cache key
            ttl: TTL in seconds (None = use default)

        Returns:
            True if successfully cached, False otherwise
        """
        start_time = time.time()

        try:
            # Generate cache key
            cache_key = self.key_generator.generate(sql, params, metadata)

            # Serialize result
            serialized = self._serialize(result)
            size_bytes = len(serialized)

            # Check size limits
            if self.max_memory_bytes and size_bytes > self.max_memory_bytes:
                logger.warning(
                    f"Result too large to cache: {size_bytes} bytes > {self.max_memory_bytes} bytes"
                )
                return False

            # Use provided TTL or default
            effective_ttl = ttl if ttl is not None else self.default_ttl

            # Put into cache
            if self.use_redis and self.redis_client:
                success = self._redis_put(cache_key, serialized, effective_ttl)
            else:
                success = self._memory_put(cache_key, serialized, size_bytes)

            # Track table -> key mapping for invalidation
            if success:
                tables = self.key_generator.extract_table_names(sql)
                for table in tables:
                    if table not in self.table_keys_map:
                        self.table_keys_map[table] = set()
                    self.table_keys_map[table].add(cache_key)

            # Record metrics
            elapsed_ms = (time.time() - start_time) * 1000
            if success and self.metrics_collector:
                self.metrics_collector.record_put(
                    put_time_ms=elapsed_ms, size_bytes=size_bytes
                )
                logger.debug(
                    f"Cache PUT: {cache_key[:16]}... ({size_bytes} bytes, {elapsed_ms:.2f}ms)"
                )

            return success

        except Exception as e:
            logger.error(f"Cache PUT error: {e}")
            if self.metrics_collector:
                self.metrics_collector.record_error()
            return False

    def invalidate(
        self,
        sql: str,
        params: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Invalidate specific cached query.

        Args:
            sql: SQL query string
            params: Query parameters
            metadata: Optional metadata

        Returns:
            True if invalidated, False otherwise
        """
        try:
            cache_key = self.key_generator.generate(sql, params, metadata)

            if self.use_redis and self.redis_client:
                deleted = self.redis_client.delete(cache_key)
                success = deleted > 0
            else:
                if cache_key in self.memory_cache:
                    size_bytes = len(self.memory_cache[cache_key])
                    del self.memory_cache[cache_key]
                    self.memory_size_bytes -= size_bytes
                    success = True
                else:
                    success = False

            if success and self.metrics_collector:
                self.metrics_collector.record_invalidation(num_keys=1)

            return success

        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return False

    def invalidate_table(self, table_name: str) -> int:
        """
        Invalidate all cached queries related to a table.

        Args:
            table_name: Table name to invalidate

        Returns:
            Number of keys invalidated
        """
        try:
            # Get keys related to this table
            if table_name in self.table_keys_map:
                keys_to_delete = list(self.table_keys_map[table_name])

                if self.use_redis and self.redis_client:
                    if keys_to_delete:
                        deleted = self.redis_client.delete(*keys_to_delete)
                    else:
                        deleted = 0
                else:
                    deleted = 0
                    for key in keys_to_delete:
                        if key in self.memory_cache:
                            size_bytes = len(self.memory_cache[key])
                            del self.memory_cache[key]
                            self.memory_size_bytes -= size_bytes
                            deleted += 1

                # Clear mapping
                del self.table_keys_map[table_name]

                if self.metrics_collector:
                    self.metrics_collector.record_invalidation(num_keys=deleted)

                logger.info(f"Invalidated {deleted} keys for table '{table_name}'")
                return deleted
            else:
                return 0

        except Exception as e:
            logger.error(f"Cache invalidate_table error: {e}")
            return 0

    def clear(self) -> bool:
        """
        Clear entire cache.

        Returns:
            True if cleared, False otherwise
        """
        try:
            if self.use_redis and self.redis_client:
                # Delete all keys with our prefix
                pattern = f"{self.key_generator.prefix}:{self.key_generator.namespace}:*"
                cursor = 0
                deleted = 0
                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor, match=pattern, count=1000
                    )
                    if keys:
                        deleted += self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
                logger.info(f"Cleared {deleted} keys from Redis cache")
            else:
                deleted = len(self.memory_cache)
                self.memory_cache.clear()
                self.memory_size_bytes = 0
                logger.info(f"Cleared {deleted} keys from in-memory cache")

            # Clear table mappings
            self.table_keys_map.clear()

            if self.metrics_collector:
                self.metrics_collector.record_invalidation(num_keys=deleted)

            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def get_metrics(self) -> CacheMetrics:
        """
        Get current cache metrics.

        Returns:
            CacheMetrics object
        """
        if self.metrics_collector:
            return self.metrics_collector.get_current_metrics()
        else:
            return CacheMetrics()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        stats = {
            "backend": "redis" if self.use_redis else "memory",
            "default_ttl": self.default_ttl,
            "max_keys": self.max_keys,
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024) if self.max_memory_bytes else None,
        }

        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info("memory")
                stats["redis_used_memory_mb"] = info.get("used_memory", 0) / (1024 * 1024)
                stats["redis_connected"] = True
            except:
                stats["redis_connected"] = False
        else:
            stats["memory_size_bytes"] = self.memory_size_bytes
            stats["memory_keys"] = len(self.memory_cache)

        # Add metrics
        if self.metrics_collector:
            metrics = self.metrics_collector.get_current_metrics()
            stats["metrics"] = metrics.to_dict()

        return stats

    # ===== Internal Methods =====

    def _redis_get(self, key: str) -> Optional[Any]:
        """Get from Redis cache."""
        if not self.redis_client:
            return None

        serialized = self.redis_client.get(key)
        if serialized:
            return self._deserialize(serialized)
        return None

    def _redis_put(self, key: str, value: bytes, ttl: int) -> bool:
        """Put into Redis cache."""
        if not self.redis_client:
            return False

        if ttl > 0:
            self.redis_client.setex(key, ttl, value)
        else:
            self.redis_client.set(key, value)
        return True

    def _memory_get(self, key: str) -> Optional[Any]:
        """Get from in-memory cache (LRU)."""
        if key in self.memory_cache:
            # Move to end (most recently used)
            self.memory_cache.move_to_end(key)
            return self._deserialize(self.memory_cache[key])
        return None

    def _memory_put(self, key: str, value: bytes, size_bytes: int) -> bool:
        """Put into in-memory cache with LRU eviction."""
        # Check if key already exists
        if key in self.memory_cache:
            old_size = len(self.memory_cache[key])
            self.memory_size_bytes -= old_size

        # Check size limit
        if self.max_memory_bytes:
            while (
                self.memory_size_bytes + size_bytes > self.max_memory_bytes
                and self.memory_cache
            ):
                self._evict_lru()

        # Check key limit
        if self.max_keys:
            while len(self.memory_cache) >= self.max_keys:
                self._evict_lru()

        # Add to cache
        self.memory_cache[key] = value
        self.memory_size_bytes += size_bytes

        # Move to end (most recently used)
        self.memory_cache.move_to_end(key)

        return True

    def _evict_lru(self):
        """Evict least recently used item from in-memory cache."""
        if not self.memory_cache:
            return

        # Remove first item (least recently used)
        key, value = self.memory_cache.popitem(last=False)
        size_bytes = len(value)
        self.memory_size_bytes -= size_bytes

        if self.metrics_collector:
            self.metrics_collector.record_eviction(size_bytes=size_bytes)

        logger.debug(f"Evicted LRU key: {key[:16]}... ({size_bytes} bytes)")

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for caching."""
        # Use pickle for Python objects
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize cached value."""
        return pickle.loads(data)


__all__ = ["QueryCache"]
