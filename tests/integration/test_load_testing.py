"""
Load Testing - 100 Concurrent Users

Comprehensive load testing for NeuroLake including:
- Concurrent query execution
- Concurrent file operations
- Cache under load
- Database connection pooling
- System resource usage
- Throughput under load
- Error rates under stress
"""

import pytest
import time
import tempfile
import shutil
import numpy as np
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
import threading
import duckdb
from collections import defaultdict
import statistics

from neurolake.cache.cache import QueryCache
from neurolake.optimizer.optimizer import QueryOptimizer


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def test_dataset():
    """Create test dataset."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(10000),
        "value": np.random.randn(10000),
        "category": np.random.choice(["A", "B", "C", "D"], 10000),
        "timestamp": pd.date_range("2024-01-01", periods=10000, freq="1min")
    })


class LoadTestMetrics:
    """Track metrics during load testing."""

    def __init__(self):
        self.response_times = []
        self.errors = []
        self.success_count = 0
        self.error_count = 0
        self.lock = threading.Lock()

    def record_success(self, response_time):
        """Record successful operation."""
        with self.lock:
            self.response_times.append(response_time)
            self.success_count += 1

    def record_error(self, error):
        """Record failed operation."""
        with self.lock:
            self.errors.append(str(error))
            self.error_count += 1

    def get_stats(self):
        """Get statistics."""
        with self.lock:
            total_requests = self.success_count + self.error_count
            error_rate = (self.error_count / total_requests * 100) if total_requests > 0 else 0

            stats = {
                "total_requests": total_requests,
                "successful": self.success_count,
                "failed": self.error_count,
                "error_rate": error_rate,
            }

            if self.response_times:
                stats.update({
                    "avg_response_time": statistics.mean(self.response_times),
                    "min_response_time": min(self.response_times),
                    "max_response_time": max(self.response_times),
                    "median_response_time": statistics.median(self.response_times),
                    "p95_response_time": statistics.quantiles(self.response_times, n=20)[18],  # 95th percentile
                    "p99_response_time": statistics.quantiles(self.response_times, n=100)[98],  # 99th percentile
                })

            return stats


class TestConcurrentQueries:
    """Test concurrent query execution."""

    @pytest.mark.slow
    def test_100_concurrent_simple_queries(self, temp_dir, test_dataset):
        """Test 100 concurrent users executing simple queries."""
        db_path = temp_dir / "load_test.db"
        conn = duckdb.connect(str(db_path))

        # Setup database
        conn.execute("CREATE TABLE data AS SELECT * FROM test_dataset")
        conn.close()

        metrics = LoadTestMetrics()

        def run_query(user_id):
            """Execute query as a user."""
            try:
                start = time.time()

                # Each user gets their own connection
                conn = duckdb.connect(str(db_path))
                result = conn.execute(
                    f"SELECT COUNT(*) FROM data WHERE value > {user_id % 10}"
                ).fetchall()
                conn.close()

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, len(result)

            except Exception as e:
                metrics.record_error(e)
                return user_id, None

        # Run 100 concurrent users
        print("\nExecuting 100 concurrent simple queries...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(run_query, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()

        print(f"\nLoad Test Results (100 users, simple queries):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Error rate: {stats['error_rate']:.2f}%")
        print(f"  Avg response time: {stats.get('avg_response_time', 0):.4f}s")
        print(f"  Median response time: {stats.get('median_response_time', 0):.4f}s")
        print(f"  P95 response time: {stats.get('p95_response_time', 0):.4f}s")
        print(f"  P99 response time: {stats.get('p99_response_time', 0):.4f}s")
        print(f"  Throughput: {100/total_time:.2f} queries/sec")

        # Assertions
        assert stats["successful"] >= 95  # At least 95% success rate
        assert stats["error_rate"] <= 5.0  # Max 5% error rate
        assert stats.get("avg_response_time", 0) < 2.0  # Avg response < 2s

    def test_50_concurrent_aggregate_queries(self, temp_dir, test_dataset):
        """Test 50 concurrent users executing aggregate queries."""
        db_path = temp_dir / "load_test.db"
        conn = duckdb.connect(str(db_path))

        # Setup database
        conn.execute("CREATE TABLE data AS SELECT * FROM test_dataset")
        conn.close()

        metrics = LoadTestMetrics()

        def run_aggregate_query(user_id):
            """Execute aggregate query."""
            try:
                start = time.time()

                conn = duckdb.connect(str(db_path))
                result = conn.execute("""
                    SELECT category, COUNT(*) as count, AVG(value) as avg_val
                    FROM data
                    GROUP BY category
                """).fetchall()
                conn.close()

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, len(result)

            except Exception as e:
                metrics.record_error(e)
                return user_id, None

        # Run 50 concurrent users
        print("\nExecuting 50 concurrent aggregate queries...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(run_aggregate_query, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()

        print(f"\nLoad Test Results (50 users, aggregate queries):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Avg response time: {stats.get('avg_response_time', 0):.4f}s")
        print(f"  Throughput: {50/total_time:.2f} queries/sec")

        assert stats["successful"] >= 48  # At least 96% success rate
        assert stats.get("avg_response_time", 0) < 3.0


class TestConcurrentFileOperations:
    """Test concurrent file operations."""

    def test_100_concurrent_file_writes(self, temp_dir):
        """Test 100 concurrent users writing files."""
        metrics = LoadTestMetrics()

        def write_file(user_id):
            """Write a file."""
            try:
                start = time.time()

                file_path = temp_dir / f"user_{user_id}.parquet"
                df = pd.DataFrame({
                    "id": range(1000),
                    "value": np.random.randn(1000),
                    "user_id": user_id
                })
                df.to_parquet(file_path, compression="snappy")

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, file_path.exists()

            except Exception as e:
                metrics.record_error(e)
                return user_id, False

        # Run 100 concurrent writes
        print("\nExecuting 100 concurrent file writes...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(write_file, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()

        print(f"\nLoad Test Results (100 users, file writes):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Avg write time: {stats.get('avg_response_time', 0):.4f}s")
        print(f"  Throughput: {100/total_time:.2f} writes/sec")

        assert stats["successful"] >= 98  # At least 98% success rate
        assert stats.get("avg_response_time", 0) < 1.0

    def test_100_concurrent_file_reads(self, temp_dir):
        """Test 100 concurrent users reading files."""
        # Setup: Write files first
        file_path = temp_dir / "shared_data.parquet"
        df = pd.DataFrame({
            "id": range(10000),
            "value": np.random.randn(10000)
        })
        df.to_parquet(file_path, compression="snappy")

        metrics = LoadTestMetrics()

        def read_file(user_id):
            """Read a file."""
            try:
                start = time.time()

                df_read = pd.read_parquet(file_path)
                row_count = len(df_read)

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, row_count

            except Exception as e:
                metrics.record_error(e)
                return user_id, 0

        # Run 100 concurrent reads
        print("\nExecuting 100 concurrent file reads...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(read_file, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()

        print(f"\nLoad Test Results (100 users, file reads):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {stats['successful']}")
        print(f"  Avg read time: {stats.get('avg_response_time', 0):.4f}s")
        print(f"  Throughput: {100/total_time:.2f} reads/sec")

        assert stats["successful"] == 100  # All should succeed
        assert stats.get("avg_response_time", 0) < 0.5


class TestCacheUnderLoad:
    """Test cache performance under load."""

    def test_cache_with_100_concurrent_users(self):
        """Test cache with 100 concurrent users."""
        cache = QueryCache(use_redis=False)
        metrics = LoadTestMetrics()

        # Pre-populate cache
        for i in range(10):
            key = cache.key_generator.generate(f"query_{i}")
            cache.put(key, {"result": list(range(1000))})

        def access_cache(user_id):
            """Access cache."""
            try:
                start = time.time()

                # 70% cache hits, 30% cache misses
                query_id = user_id % 14  # Some queries will hit cache, some won't

                key = cache.key_generator.generate(f"query_{query_id}")
                result = cache.get(key)

                if result is None:
                    # Cache miss - populate
                    cache.put(key, {"result": list(range(1000))})

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, result is not None

            except Exception as e:
                metrics.record_error(e)
                return user_id, False

        # Run 100 concurrent cache accesses
        print("\nExecuting 100 concurrent cache accesses...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(access_cache, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()
        cache_stats = cache.get_stats()

        print(f"\nLoad Test Results (100 users, cache access):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {stats['successful']}")
        print(f"  Avg access time: {stats.get('avg_response_time', 0):.6f}s")
        print(f"  Cache size: {cache_stats.get('size', 0)}")

        assert stats["successful"] == 100
        assert stats.get("avg_response_time", 0) < 0.01  # Cache should be very fast


class TestOptimizerUnderLoad:
    """Test optimizer performance under load."""

    def test_optimizer_with_50_concurrent_users(self):
        """Test optimizer with 50 concurrent users."""
        queries = [
            "SELECT * FROM users WHERE age > 18",
            "SELECT COUNT(*) FROM orders WHERE status = 'active'",
            "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id",
            "SELECT category, AVG(price) FROM products GROUP BY category",
            "SELECT * FROM logs WHERE timestamp > '2024-01-01' ORDER BY id LIMIT 100"
        ]

        metrics = LoadTestMetrics()

        def optimize_query(user_id):
            """Optimize a query."""
            try:
                start = time.time()

                optimizer = QueryOptimizer()
                query = queries[user_id % len(queries)]
                optimized = optimizer.optimize(query)

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, optimized is not None

            except Exception as e:
                metrics.record_error(e)
                return user_id, False

        # Run 50 concurrent optimizations
        print("\nExecuting 50 concurrent query optimizations...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(optimize_query, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()

        print(f"\nLoad Test Results (50 users, query optimization):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {stats['successful']}")
        print(f"  Avg optimization time: {stats.get('avg_response_time', 0):.4f}s")

        assert stats["successful"] >= 48
        assert stats.get("avg_response_time", 0) < 1.0


class TestMixedWorkload:
    """Test mixed workload scenarios."""

    def test_mixed_workload_100_users(self, temp_dir, test_dataset):
        """Test 100 users with mixed operations (read/write/query)."""
        db_path = temp_dir / "mixed_load.db"
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE data AS SELECT * FROM test_dataset")
        conn.close()

        metrics_by_operation = {
            "query": LoadTestMetrics(),
            "read": LoadTestMetrics(),
            "write": LoadTestMetrics()
        }

        def execute_operation(user_id):
            """Execute mixed operation based on user_id."""
            operation_type = ["query", "read", "write"][user_id % 3]
            metrics = metrics_by_operation[operation_type]

            try:
                start = time.time()

                if operation_type == "query":
                    # Query operation
                    conn = duckdb.connect(str(db_path))
                    conn.execute("SELECT COUNT(*) FROM data WHERE value > 0").fetchall()
                    conn.close()

                elif operation_type == "read":
                    # File read operation
                    file_path = temp_dir / "shared.parquet"
                    if not file_path.exists():
                        test_dataset.to_parquet(file_path)
                    pd.read_parquet(file_path)

                elif operation_type == "write":
                    # File write operation
                    file_path = temp_dir / f"user_{user_id}.csv"
                    small_df = pd.DataFrame({"id": range(100), "value": range(100)})
                    small_df.to_csv(file_path, index=False)

                elapsed = time.time() - start
                metrics.record_success(elapsed)
                return user_id, operation_type

            except Exception as e:
                metrics.record_error(e)
                return user_id, None

        # Run 100 users with mixed operations
        print("\nExecuting 100 users with mixed workload...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(execute_operation, i) for i in range(100)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics for each operation type
        print(f"\nMixed Workload Results (100 users, {total_time:.2f}s total):")

        for op_type, metrics in metrics_by_operation.items():
            stats = metrics.get_stats()
            if stats["total_requests"] > 0:
                print(f"\n  {op_type.upper()}:")
                print(f"    Requests: {stats['total_requests']}")
                print(f"    Successful: {stats['successful']}")
                print(f"    Failed: {stats['failed']}")
                print(f"    Avg time: {stats.get('avg_response_time', 0):.4f}s")

        # Overall assertions
        total_successful = sum(m.success_count for m in metrics_by_operation.values())
        assert total_successful >= 92  # At least 92% overall success rate (accounting for variance)


class TestSystemStress:
    """Test system under stress conditions."""

    def test_sustained_load_30_seconds(self, temp_dir, test_dataset):
        """Test sustained load for 30 seconds."""
        db_path = temp_dir / "stress_test.db"
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE data AS SELECT * FROM test_dataset")
        conn.close()

        metrics = LoadTestMetrics()
        stop_flag = threading.Event()

        def continuous_queries(worker_id):
            """Execute queries continuously."""
            query_count = 0

            while not stop_flag.is_set():
                try:
                    start = time.time()

                    conn = duckdb.connect(str(db_path))
                    conn.execute("SELECT COUNT(*) FROM data WHERE value > 0").fetchall()
                    conn.close()

                    elapsed = time.time() - start
                    metrics.record_success(elapsed)
                    query_count += 1

                except Exception as e:
                    metrics.record_error(e)

            return worker_id, query_count

        # Run sustained load for 30 seconds with 20 workers
        print("\nExecuting sustained load (20 workers, 30 seconds)...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(continuous_queries, i) for i in range(20)]

            # Let it run for 30 seconds
            time.sleep(30)
            stop_flag.set()

            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time

        # Get statistics
        stats = metrics.get_stats()

        print(f"\nSustained Load Results ({total_time:.1f}s):")
        print(f"  Total queries: {stats['total_requests']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Error rate: {stats['error_rate']:.2f}%")
        print(f"  Avg response time: {stats.get('avg_response_time', 0):.4f}s")
        print(f"  Throughput: {stats['total_requests']/total_time:.2f} queries/sec")

        assert stats["error_rate"] <= 5.0  # Max 5% error rate under sustained load
        assert stats["total_requests"] > 200  # Should handle at least 200 queries


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
