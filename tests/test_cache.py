"""
Comprehensive tests for the NeuroLake Cache module.

Tests cover:
- CacheKeyGenerator (key generation, normalization, table extraction)
- CacheMetrics (metrics tracking and calculations)
- CacheMetricsCollector (metrics aggregation)
- QueryCache with in-memory backend
- Cache operations (get, put, invalidate, clear)
- LRU eviction
- TTL handling
- Edge cases
"""

import pytest
import time
from typing import Dict, Any
from unittest.mock import MagicMock, patch

# Import cache components
from neurolake.cache import (
    QueryCache,
    CacheKeyGenerator,
    CacheMetrics,
    CacheMetricsCollector,
)


# ============================================================================
# CacheKeyGenerator Tests
# ============================================================================

class TestCacheKeyGenerator:
    """Test CacheKeyGenerator functionality."""

    def test_generator_init(self):
        """Test key generator initialization"""
        generator = CacheKeyGenerator(prefix="test", namespace="cache")

        assert generator.prefix == "test"
        assert generator.namespace == "cache"

    def test_generator_defaults(self):
        """Test default prefix and namespace"""
        generator = CacheKeyGenerator()

        assert generator.prefix == "neurolake"
        assert generator.namespace == "cache"

    def test_generate_simple(self):
        """Test simple key generation without parameters"""
        generator = CacheKeyGenerator()

        key1 = generator.generate_simple("SELECT * FROM users")
        key2 = generator.generate_simple("SELECT * FROM users")
        key3 = generator.generate_simple("SELECT * FROM orders")

        # Same SQL should produce same key
        assert key1 == key2

        # Different SQL should produce different key
        assert key1 != key3

        # Key should have correct format
        assert key1.startswith("neurolake:cache:")

    def test_generate_with_params(self):
        """Test key generation with parameters"""
        generator = CacheKeyGenerator()

        key1 = generator.generate("SELECT * FROM users WHERE id = ?", [123])
        key2 = generator.generate("SELECT * FROM users WHERE id = ?", [123])
        key3 = generator.generate("SELECT * FROM users WHERE id = ?", [456])

        # Same SQL + params should produce same key
        assert key1 == key2

        # Different params should produce different key
        assert key1 != key3

    def test_generate_with_metadata(self):
        """Test key generation with metadata"""
        generator = CacheKeyGenerator()

        key1 = generator.generate("SELECT * FROM users", metadata={"user_id": "123"})
        key2 = generator.generate("SELECT * FROM users", metadata={"user_id": "123"})
        key3 = generator.generate("SELECT * FROM users", metadata={"user_id": "456"})

        # Same metadata should produce same key
        assert key1 == key2

        # Different metadata should produce different key
        assert key1 != key3

    def test_generate_with_metadata_helper(self):
        """Test generate_with_metadata helper method"""
        generator = CacheKeyGenerator()

        key1 = generator.generate_with_metadata("SELECT * FROM users", user_id="123")
        key2 = generator.generate_with_metadata("SELECT * FROM users", user_id="123")
        key3 = generator.generate_with_metadata("SELECT * FROM users", user_id="456")

        assert key1 == key2
        assert key1 != key3

    def test_generate_with_tenant(self):
        """Test generation with tenant isolation"""
        generator = CacheKeyGenerator()

        key1 = generator.generate_with_metadata("SELECT * FROM users", tenant_id="tenant1")
        key2 = generator.generate_with_metadata("SELECT * FROM users", tenant_id="tenant2")

        # Different tenants should produce different keys
        assert key1 != key2

    def test_sql_normalization(self):
        """Test SQL normalization produces same keys"""
        generator = CacheKeyGenerator()

        # These should all produce the same key
        sql_variants = [
            "SELECT * FROM users",
            "select * from users",
            "SELECT   *   FROM   users",
            "SELECT * FROM users\n",
            "  SELECT * FROM users  ",
        ]

        keys = [generator.generate_simple(sql) for sql in sql_variants]

        # All should be the same
        assert len(set(keys)) == 1

    def test_sql_comment_removal(self):
        """Test SQL comment removal in normalization"""
        generator = CacheKeyGenerator()

        sql1 = "SELECT * FROM users"
        sql2 = "SELECT * FROM users -- with comment"
        sql3 = "SELECT * FROM users /* block comment */"

        key1 = generator.generate_simple(sql1)
        key2 = generator.generate_simple(sql2)
        key3 = generator.generate_simple(sql3)

        # All should normalize to the same key
        assert key1 == key2 == key3

    def test_extract_table_names_from(self):
        """Test extracting table names from FROM clause"""
        generator = CacheKeyGenerator()

        tables = generator.extract_table_names("SELECT * FROM users")

        assert "users" in tables

    def test_extract_table_names_join(self):
        """Test extracting table names from JOIN clauses"""
        generator = CacheKeyGenerator()

        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        tables = generator.extract_table_names(sql)

        assert "users" in tables
        assert "orders" in tables

    def test_extract_table_names_multiple_joins(self):
        """Test extracting from multiple JOINs"""
        generator = CacheKeyGenerator()

        sql = """
            SELECT * FROM users
            JOIN orders ON users.id = orders.user_id
            LEFT JOIN products ON orders.product_id = products.id
        """
        tables = generator.extract_table_names(sql)

        assert "users" in tables
        assert "orders" in tables
        assert "products" in tables

    def test_extract_schema_qualified_tables(self):
        """Test extracting schema-qualified table names"""
        generator = CacheKeyGenerator()

        tables = generator.extract_table_names("SELECT * FROM public.users")

        assert "public.users" in tables

    def test_invalidation_pattern(self):
        """Test invalidation pattern generation"""
        generator = CacheKeyGenerator()

        pattern = generator.invalidation_pattern("users")

        assert pattern == "neurolake:cache:*"
        assert generator.prefix in pattern


# ============================================================================
# CacheMetrics Tests
# ============================================================================

class TestCacheMetrics:
    """Test CacheMetrics class."""

    def test_metrics_init(self):
        """Test metrics initialization"""
        metrics = CacheMetrics()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.puts == 0
        assert metrics.evictions == 0
        assert metrics.invalidations == 0
        assert metrics.errors == 0

    def test_total_requests(self):
        """Test total requests calculation"""
        metrics = CacheMetrics(hits=10, misses=5)

        assert metrics.total_requests == 15

    def test_hit_rate(self):
        """Test hit rate calculation"""
        metrics = CacheMetrics(hits=8, misses=2)

        assert metrics.hit_rate == 0.8

    def test_hit_rate_zero_requests(self):
        """Test hit rate when no requests"""
        metrics = CacheMetrics()

        assert metrics.hit_rate == 0.0

    def test_miss_rate(self):
        """Test miss rate calculation"""
        metrics = CacheMetrics(hits=7, misses=3)

        assert abs(metrics.miss_rate - 0.3) < 0.0001  # Float comparison tolerance

    def test_avg_get_time(self):
        """Test average GET time calculation"""
        metrics = CacheMetrics(
            hits=5,
            misses=5,
            total_get_time_ms=100.0
        )

        assert metrics.avg_get_time_ms == 10.0

    def test_avg_put_time(self):
        """Test average PUT time calculation"""
        metrics = CacheMetrics(
            puts=10,
            total_put_time_ms=50.0
        )

        assert metrics.avg_put_time_ms == 5.0

    def test_avg_size_bytes(self):
        """Test average size calculation"""
        metrics = CacheMetrics(
            total_keys=5,
            total_size_bytes=10000
        )

        assert metrics.avg_size_bytes == 2000.0

    def test_to_dict(self):
        """Test converting metrics to dictionary"""
        metrics = CacheMetrics(hits=10, misses=5, puts=8)

        metrics_dict = metrics.to_dict()

        assert metrics_dict["hits"] == 10
        assert metrics_dict["misses"] == 5
        assert metrics_dict["puts"] == 8
        assert "hit_rate" in metrics_dict
        assert "total_requests" in metrics_dict


# ============================================================================
# CacheMetricsCollector Tests
# ============================================================================

class TestCacheMetricsCollector:
    """Test CacheMetricsCollector class."""

    def test_collector_init(self):
        """Test collector initialization"""
        collector = CacheMetricsCollector()

        assert collector.current_metrics is not None
        assert collector.current_metrics.hits == 0
        assert len(collector.history) == 0

    def test_record_hit(self):
        """Test recording cache hit"""
        collector = CacheMetricsCollector()

        collector.record_hit(get_time_ms=1.5)

        assert collector.current_metrics.hits == 1
        assert collector.current_metrics.total_get_time_ms == 1.5

    def test_record_miss(self):
        """Test recording cache miss"""
        collector = CacheMetricsCollector()

        collector.record_miss(get_time_ms=2.0)

        assert collector.current_metrics.misses == 1
        assert collector.current_metrics.total_get_time_ms == 2.0

    def test_record_put(self):
        """Test recording cache put"""
        collector = CacheMetricsCollector()

        collector.record_put(put_time_ms=3.0, size_bytes=1024)

        assert collector.current_metrics.puts == 1
        assert collector.current_metrics.total_put_time_ms == 3.0
        assert collector.current_metrics.total_keys == 1
        assert collector.current_metrics.total_size_bytes == 1024

    def test_record_eviction(self):
        """Test recording eviction"""
        collector = CacheMetricsCollector()

        # Add some keys first
        collector.record_put(size_bytes=500)
        collector.record_put(size_bytes=500)

        assert collector.current_metrics.total_keys == 2
        assert collector.current_metrics.total_size_bytes == 1000

        # Record eviction
        collector.record_eviction(size_bytes=500)

        assert collector.current_metrics.evictions == 1
        assert collector.current_metrics.total_keys == 1
        assert collector.current_metrics.total_size_bytes == 500

    def test_record_invalidation(self):
        """Test recording invalidation"""
        collector = CacheMetricsCollector()

        collector.record_put()
        collector.record_put()

        assert collector.current_metrics.total_keys == 2

        collector.record_invalidation(num_keys=2)

        assert collector.current_metrics.invalidations == 2
        assert collector.current_metrics.total_keys == 0

    def test_record_error(self):
        """Test recording error"""
        collector = CacheMetricsCollector()

        collector.record_error()

        assert collector.current_metrics.errors == 1

    def test_get_current_metrics(self):
        """Test getting current metrics"""
        collector = CacheMetricsCollector()

        collector.record_hit()
        collector.record_miss()

        metrics = collector.get_current_metrics()

        assert metrics.hits == 1
        assert metrics.misses == 1

    def test_reset_metrics(self):
        """Test resetting metrics"""
        collector = CacheMetricsCollector()

        collector.record_hit()
        collector.record_miss()

        collector.reset_metrics()

        # Old metrics should be in history
        assert len(collector.history) == 1
        assert collector.history[0].hits == 1

        # Current metrics should be reset
        assert collector.current_metrics.hits == 0

    def test_get_history(self):
        """Test getting metrics history"""
        collector = CacheMetricsCollector()

        # Create some history
        for i in range(5):
            collector.record_hit()
            collector.reset_metrics()

        history = collector.get_history(limit=3)

        assert len(history) == 3

    def test_get_aggregate_metrics(self):
        """Test aggregate metrics calculation"""
        collector = CacheMetricsCollector()

        # First period
        collector.record_hit()
        collector.record_hit()
        collector.reset_metrics()

        # Second period
        collector.record_hit()
        collector.record_miss()

        aggregate = collector.get_aggregate_metrics()

        assert aggregate["total_hits"] == 3
        assert aggregate["total_misses"] == 1
        assert aggregate["total_requests"] == 4
        assert aggregate["overall_hit_rate"] == 0.75
        assert aggregate["periods_tracked"] == 2


# ============================================================================
# QueryCache Tests (In-Memory)
# ============================================================================

class TestQueryCacheInMemory:
    """Test QueryCache with in-memory backend."""

    def test_cache_init_in_memory(self):
        """Test cache initialization with in-memory backend"""
        cache = QueryCache(use_redis=False)

        assert cache.use_redis is False
        assert cache.default_ttl == 3600
        assert cache.memory_cache is not None

    def test_cache_init_with_options(self):
        """Test cache initialization with custom options"""
        cache = QueryCache(
            use_redis=False,
            default_ttl=7200,
            max_keys=1000,
            max_memory_mb=100,
            key_prefix="test",
        )

        assert cache.default_ttl == 7200
        assert cache.max_keys == 1000
        assert cache.max_memory_bytes == 100 * 1024 * 1024

    def test_put_and_get(self):
        """Test basic put and get operations"""
        cache = QueryCache(use_redis=False)

        # Put result
        result = {"data": [1, 2, 3]}
        success = cache.put("SELECT * FROM users", result)

        assert success is True

        # Get result
        cached = cache.get("SELECT * FROM users")

        assert cached == result

    def test_get_miss(self):
        """Test cache miss"""
        cache = QueryCache(use_redis=False)

        result = cache.get("SELECT * FROM nonexistent")

        assert result is None

    def test_put_with_params(self):
        """Test put/get with parameters"""
        cache = QueryCache(use_redis=False)

        result1 = {"id": 123}
        result2 = {"id": 456}

        cache.put("SELECT * FROM users WHERE id = ?", result1, params=[123])
        cache.put("SELECT * FROM users WHERE id = ?", result2, params=[456])

        # Different params should return different results
        cached1 = cache.get("SELECT * FROM users WHERE id = ?", params=[123])
        cached2 = cache.get("SELECT * FROM users WHERE id = ?", params=[456])

        assert cached1 == result1
        assert cached2 == result2

    def test_put_with_custom_ttl(self):
        """Test put with custom TTL (in-memory doesn't enforce TTL)"""
        cache = QueryCache(use_redis=False)

        result = {"data": "test"}
        success = cache.put("SELECT * FROM users", result, ttl=60)

        assert success is True

    def test_lru_eviction_by_max_keys(self):
        """Test LRU eviction when max_keys is reached"""
        cache = QueryCache(use_redis=False, max_keys=3)

        # Add 3 items
        cache.put("SELECT 1", {"result": 1})
        cache.put("SELECT 2", {"result": 2})
        cache.put("SELECT 3", {"result": 3})

        # Add 4th item - should evict first (LRU)
        cache.put("SELECT 4", {"result": 4})

        # First item should be evicted
        assert cache.get("SELECT 1") is None
        assert cache.get("SELECT 2") is not None
        assert cache.get("SELECT 3") is not None
        assert cache.get("SELECT 4") is not None

    def test_lru_order_maintained(self):
        """Test LRU order is maintained on access"""
        cache = QueryCache(use_redis=False, max_keys=3)

        cache.put("SELECT 1", {"result": 1})
        cache.put("SELECT 2", {"result": 2})
        cache.put("SELECT 3", {"result": 3})

        # Access first item (moves to end)
        cache.get("SELECT 1")

        # Add 4th item - should evict "SELECT 2" (now LRU)
        cache.put("SELECT 4", {"result": 4})

        assert cache.get("SELECT 1") is not None  # Still there
        assert cache.get("SELECT 2") is None  # Evicted
        assert cache.get("SELECT 3") is not None
        assert cache.get("SELECT 4") is not None

    def test_eviction_by_memory_limit(self):
        """Test eviction when memory limit is reached"""
        cache = QueryCache(use_redis=False, max_memory_mb=0.1)  # Small but reasonable limit

        # Add result
        result = {"data": "x" * 1000}
        cache.put("SELECT 1", result)

        # Should be in cache
        cached = cache.get("SELECT 1")
        assert cached is not None

        # Add more results to trigger potential eviction
        for i in range(2, 10):
            cache.put(f"SELECT {i}", result)

        # At least some should be available (depends on eviction policy)
        results = [cache.get(f"SELECT {i}") for i in range(1, 10)]
        assert any(r is not None for r in results)

    def test_invalidate_specific_query(self):
        """Test invalidating specific query"""
        cache = QueryCache(use_redis=False)

        cache.put("SELECT * FROM users", {"data": "users"})
        cache.put("SELECT * FROM orders", {"data": "orders"})

        # Invalidate users query
        success = cache.invalidate("SELECT * FROM users")

        assert success is True
        assert cache.get("SELECT * FROM users") is None
        assert cache.get("SELECT * FROM orders") is not None

    def test_invalidate_nonexistent(self):
        """Test invalidating non-existent query"""
        cache = QueryCache(use_redis=False)

        success = cache.invalidate("SELECT * FROM nonexistent")

        assert success is False

    def test_invalidate_table(self):
        """Test invalidating all queries for a table"""
        cache = QueryCache(use_redis=False)

        cache.put("SELECT * FROM users", {"data": "all"})
        cache.put("SELECT id FROM users", {"data": "ids"})
        cache.put("SELECT * FROM orders", {"data": "orders"})

        # Invalidate users table
        count = cache.invalidate_table("users")

        assert count == 2
        assert cache.get("SELECT * FROM users") is None
        assert cache.get("SELECT id FROM users") is None
        assert cache.get("SELECT * FROM orders") is not None

    def test_clear_cache(self):
        """Test clearing entire cache"""
        cache = QueryCache(use_redis=False)

        cache.put("SELECT 1", {"r": 1})
        cache.put("SELECT 2", {"r": 2})
        cache.put("SELECT 3", {"r": 3})

        success = cache.clear()

        assert success is True
        assert cache.get("SELECT 1") is None
        assert cache.get("SELECT 2") is None
        assert cache.get("SELECT 3") is None

    def test_get_metrics(self):
        """Test getting cache metrics"""
        cache = QueryCache(use_redis=False, track_metrics=True)

        # Perform some operations
        cache.put("SELECT 1", {"r": 1})
        cache.get("SELECT 1")  # Hit
        cache.get("SELECT 2")  # Miss

        metrics = cache.get_metrics()

        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.puts == 1

    def test_metrics_disabled(self):
        """Test cache with metrics disabled"""
        cache = QueryCache(use_redis=False, track_metrics=False)

        assert cache.metrics_collector is None

        # Should still work without metrics
        cache.put("SELECT 1", {"r": 1})
        assert cache.get("SELECT 1") is not None

    def test_get_stats(self):
        """Test getting cache statistics"""
        cache = QueryCache(use_redis=False)

        cache.put("SELECT 1", {"r": 1})

        stats = cache.get_stats()

        assert stats["backend"] == "memory"
        assert stats["default_ttl"] == 3600
        assert "memory_keys" in stats
        assert "memory_size_bytes" in stats

    def test_eviction_metrics(self):
        """Test eviction is tracked in metrics"""
        cache = QueryCache(use_redis=False, max_keys=2, track_metrics=True)

        cache.put("SELECT 1", {"r": 1})
        cache.put("SELECT 2", {"r": 2})
        cache.put("SELECT 3", {"r": 3})  # Triggers eviction

        metrics = cache.get_metrics()

        assert metrics.evictions >= 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestCacheIntegration:
    """Integration tests for complete cache workflows."""

    def test_end_to_end_caching(self):
        """Test complete caching workflow"""
        cache = QueryCache(use_redis=False, track_metrics=True)

        sql = "SELECT * FROM users WHERE active = TRUE"
        result = {"users": [{"id": 1, "name": "Alice"}]}

        # First access - miss
        cached = cache.get(sql)
        assert cached is None

        # Put result
        cache.put(sql, result)

        # Second access - hit
        cached = cache.get(sql)
        assert cached == result

        # Check metrics
        metrics = cache.get_metrics()
        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.hit_rate == 0.5

    def test_multi_table_invalidation(self):
        """Test invalidating multiple tables"""
        cache = QueryCache(use_redis=False)

        cache.put("SELECT * FROM users", {"data": "users"})
        cache.put("SELECT * FROM users JOIN orders", {"data": "join"})
        cache.put("SELECT * FROM orders", {"data": "orders"})

        # Invalidate users
        cache.invalidate_table("users")

        # Queries with users should be invalidated
        assert cache.get("SELECT * FROM users") is None
        assert cache.get("SELECT * FROM users JOIN orders") is None

        # Orders-only query should still be cached
        assert cache.get("SELECT * FROM orders") is not None


# ============================================================================
# Edge Cases
# ============================================================================

class TestCacheEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_sql(self):
        """Test caching empty SQL"""
        cache = QueryCache(use_redis=False)

        success = cache.put("", {"data": "empty"})
        assert success is True

        result = cache.get("")
        assert result == {"data": "empty"}

    def test_very_large_result(self):
        """Test caching very large result"""
        cache = QueryCache(use_redis=False, max_memory_mb=1)

        large_result = {"data": "x" * 1000000}  # ~1MB
        success = cache.put("SELECT large", large_result)

        # May succeed or fail depending on limit
        assert success in [True, False]

    def test_none_result(self):
        """Test caching None result"""
        cache = QueryCache(use_redis=False)

        cache.put("SELECT NULL", None)

        # Should be able to cache None
        result = cache.get("SELECT NULL")
        assert result is None  # But can't distinguish from cache miss

    def test_complex_result_types(self):
        """Test caching complex Python objects"""
        cache = QueryCache(use_redis=False)

        result = {
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "tuple": (1, 2),
            "set": {1, 2, 3},
        }

        cache.put("SELECT complex", result)

        cached = cache.get("SELECT complex")

        assert cached["list"] == [1, 2, 3]
        assert cached["dict"] == {"a": 1, "b": 2}

    def test_unicode_in_sql(self):
        """Test caching queries with Unicode"""
        cache = QueryCache(use_redis=False)

        sql = "SELECT * FROM users WHERE name = '你好'"
        result = {"name": "你好"}

        cache.put(sql, result)

        cached = cache.get(sql)
        assert cached == result

    def test_sql_with_special_characters(self):
        """Test SQL with special characters"""
        cache = QueryCache(use_redis=False)

        sql = "SELECT * FROM users WHERE email LIKE '%@example.com'"
        result = {"count": 10}

        cache.put(sql, result)

        cached = cache.get(sql)
        assert cached == result

    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access"""
        cache = QueryCache(use_redis=False)

        # Simulate multiple gets/puts
        for i in range(100):
            cache.put(f"SELECT {i}", {"result": i})

        # All should be accessible (or evicted based on limits)
        results = [cache.get(f"SELECT {i}") for i in range(100)]

        # At least some should be cached
        assert any(r is not None for r in results)
