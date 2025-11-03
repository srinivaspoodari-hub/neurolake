"""
Cache Metrics

Track cache performance metrics (hits, misses, evictions, etc.).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CacheMetrics:
    """
    Cache performance metrics for a time period.

    Tracks:
    - Hit/miss counts and rates
    - Eviction counts
    - Size statistics
    - Timing information
    """

    hits: int = 0
    misses: int = 0
    puts: int = 0
    evictions: int = 0
    invalidations: int = 0
    errors: int = 0

    # Size metrics
    total_keys: int = 0
    total_size_bytes: int = 0

    # Timing metrics (milliseconds)
    total_get_time_ms: float = 0.0
    total_put_time_ms: float = 0.0

    # Time range
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def total_requests(self) -> int:
        """Total cache requests (hits + misses)."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0.0 - 1.0)."""
        total = self.total_requests
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Cache miss rate (0.0 - 1.0)."""
        return 1.0 - self.hit_rate

    @property
    def avg_get_time_ms(self) -> float:
        """Average GET operation time in milliseconds."""
        total = self.hits + self.misses
        return self.total_get_time_ms / total if total > 0 else 0.0

    @property
    def avg_put_time_ms(self) -> float:
        """Average PUT operation time in milliseconds."""
        return self.total_put_time_ms / self.puts if self.puts > 0 else 0.0

    @property
    def avg_size_bytes(self) -> float:
        """Average cached value size in bytes."""
        return self.total_size_bytes / self.total_keys if self.total_keys > 0 else 0.0

    def to_dict(self) -> Dict:
        """
        Convert metrics to dictionary.

        Returns:
            Dictionary with all metrics
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "puts": self.puts,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "total_keys": self.total_keys,
            "total_size_bytes": self.total_size_bytes,
            "avg_size_bytes": self.avg_size_bytes,
            "total_get_time_ms": self.total_get_time_ms,
            "total_put_time_ms": self.total_put_time_ms,
            "avg_get_time_ms": self.avg_get_time_ms,
            "avg_put_time_ms": self.avg_put_time_ms,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class CacheMetricsCollector:
    """
    Collect and aggregate cache metrics over time.

    Example:
        collector = CacheMetricsCollector()

        collector.record_hit(get_time_ms=1.5)
        collector.record_miss(get_time_ms=2.0)
        collector.record_put(put_time_ms=3.0, size_bytes=1024)

        metrics = collector.get_current_metrics()
        print(f"Hit rate: {metrics.hit_rate:.2%}")
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.current_metrics = CacheMetrics()
        self.history: List[CacheMetrics] = []

    def record_hit(self, get_time_ms: float = 0.0):
        """
        Record cache hit.

        Args:
            get_time_ms: Time taken for GET operation
        """
        self.current_metrics.hits += 1
        self.current_metrics.total_get_time_ms += get_time_ms

    def record_miss(self, get_time_ms: float = 0.0):
        """
        Record cache miss.

        Args:
            get_time_ms: Time taken for GET operation
        """
        self.current_metrics.misses += 1
        self.current_metrics.total_get_time_ms += get_time_ms

    def record_put(self, put_time_ms: float = 0.0, size_bytes: int = 0):
        """
        Record cache put.

        Args:
            put_time_ms: Time taken for PUT operation
            size_bytes: Size of cached value in bytes
        """
        self.current_metrics.puts += 1
        self.current_metrics.total_put_time_ms += put_time_ms
        self.current_metrics.total_keys += 1
        self.current_metrics.total_size_bytes += size_bytes

    def record_eviction(self, size_bytes: int = 0):
        """
        Record cache eviction.

        Args:
            size_bytes: Size of evicted value in bytes
        """
        self.current_metrics.evictions += 1
        self.current_metrics.total_keys = max(0, self.current_metrics.total_keys - 1)
        self.current_metrics.total_size_bytes = max(
            0, self.current_metrics.total_size_bytes - size_bytes
        )

    def record_invalidation(self, num_keys: int = 1):
        """
        Record cache invalidation.

        Args:
            num_keys: Number of keys invalidated
        """
        self.current_metrics.invalidations += num_keys
        self.current_metrics.total_keys = max(
            0, self.current_metrics.total_keys - num_keys
        )

    def record_error(self):
        """Record cache error."""
        self.current_metrics.errors += 1

    def get_current_metrics(self) -> CacheMetrics:
        """
        Get current metrics snapshot.

        Returns:
            Current CacheMetrics
        """
        return self.current_metrics

    def reset_metrics(self):
        """
        Reset current metrics and save to history.

        Useful for periodic metric collection.
        """
        self.current_metrics.end_time = datetime.now()
        self.history.append(self.current_metrics)
        self.current_metrics = CacheMetrics()

    def get_history(self, limit: int = 10) -> List[CacheMetrics]:
        """
        Get recent metrics history.

        Args:
            limit: Maximum number of historical periods to return

        Returns:
            List of historical CacheMetrics
        """
        return self.history[-limit:] if self.history else []

    def get_aggregate_metrics(self) -> Dict:
        """
        Get aggregate metrics across all history.

        Returns:
            Dictionary with aggregate statistics
        """
        if not self.history:
            return self.current_metrics.to_dict()

        total_hits = sum(m.hits for m in self.history) + self.current_metrics.hits
        total_misses = sum(m.misses for m in self.history) + self.current_metrics.misses
        total_puts = sum(m.puts for m in self.history) + self.current_metrics.puts
        total_evictions = (
            sum(m.evictions for m in self.history) + self.current_metrics.evictions
        )
        total_requests = total_hits + total_misses

        return {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_puts": total_puts,
            "total_evictions": total_evictions,
            "total_requests": total_requests,
            "overall_hit_rate": total_hits / total_requests if total_requests > 0 else 0.0,
            "periods_tracked": len(self.history) + 1,
        }


__all__ = ["CacheMetrics", "CacheMetricsCollector"]
