"""
Performance Benchmarks

Comprehensive performance testing for NeuroLake including:
- Query execution performance
- NCF file I/O performance
- Cache performance
- Storage format comparisons
- Optimizer performance
- Concurrent operations
"""

import pytest
import time
import tempfile
import shutil
import numpy as np
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import duckdb

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType
from neurolake.optimizer.optimizer import QueryOptimizer
from neurolake.cache.cache import QueryCache


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def small_dataset():
    """Create small dataset (1K rows)."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1000),
        "value": np.random.randn(1000),
        "category": np.random.choice(["A", "B", "C"], 1000),
        "timestamp": pd.date_range("2024-01-01", periods=1000, freq="1min")
    })


@pytest.fixture
def medium_dataset():
    """Create medium dataset (100K rows)."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(100000),
        "value": np.random.randn(100000),
        "category": np.random.choice(["A", "B", "C", "D", "E"], 100000),
        "timestamp": pd.date_range("2024-01-01", periods=100000, freq="1s")
    })


@pytest.fixture
def large_dataset():
    """Create large dataset (1M rows)."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1000000),
        "value": np.random.randn(1000000),
        "category": np.random.choice(["A", "B", "C", "D", "E"], 1000000),
        "timestamp": pd.date_range("2024-01-01", periods=1000000, freq="100ms")
    })


class TestNCFPerformance:
    """Test NCF format performance."""

    def test_ncf_write_performance_small(self, temp_dir, small_dataset):
        """Benchmark NCF write performance with small dataset."""
        ncf_path = temp_dir / "small.ncf"

        schema = NCFSchema(
            table_name="small_data",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="timestamp", data_type=NCFDataType.TIMESTAMP)
            ]
        )

        start = time.time()
        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(small_dataset)
        elapsed = time.time() - start

        # Verify file was created
        assert ncf_path.exists()
        print(f"\nNCF write (1K rows): {elapsed:.4f}s")
        assert elapsed < 2.0  # Should be fast

    def test_ncf_read_performance_small(self, temp_dir, small_dataset):
        """Benchmark NCF read performance with small dataset."""
        ncf_path = temp_dir / "small.ncf"

        # Write file first
        schema = NCFSchema(
            table_name="small_data",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="timestamp", data_type=NCFDataType.TIMESTAMP)
            ]
        )

        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(small_dataset)

        start = time.time()
        with NCFReader(str(ncf_path)) as reader:
            df = reader.read()
            row_count = len(df)
        elapsed = time.time() - start

        print(f"\nNCF read (1K rows): {elapsed:.4f}s")
        assert row_count == 1000
        assert elapsed < 2.0  # Should be fast

    @pytest.mark.slow
    def test_ncf_write_performance_medium(self, temp_dir, medium_dataset):
        """Benchmark NCF write performance with medium dataset."""
        ncf_path = temp_dir / "medium.ncf"

        schema = NCFSchema(
            table_name="medium_data",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="timestamp", data_type=NCFDataType.TIMESTAMP)
            ]
        )

        start = time.time()
        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(medium_dataset)
        elapsed = time.time() - start

        assert ncf_path.exists()
        rows_per_sec = len(medium_dataset) / elapsed
        print(f"\nNCF write (100K rows): {elapsed:.2f}s ({rows_per_sec:.0f} rows/sec)")

        # Should be reasonably fast
        assert elapsed < 10.0  # Less than 10 seconds for 100K rows


class TestStorageFormatComparison:
    """Compare performance across storage formats."""

    def test_format_comparison_write(self, temp_dir, small_dataset):
        """Compare write performance: Parquet vs CSV."""
        parquet_path = temp_dir / "test.parquet"
        csv_path = temp_dir / "test.csv"

        # Measure Parquet write
        start = time.time()
        small_dataset.to_parquet(parquet_path, compression="snappy")
        parquet_time = time.time() - start

        # Measure CSV write
        start = time.time()
        small_dataset.to_csv(csv_path, index=False)
        csv_time = time.time() - start

        print(f"\nParquet write: {parquet_time:.4f}s")
        print(f"CSV write: {csv_time:.4f}s")

        assert parquet_path.exists()
        assert csv_path.exists()

    def test_format_comparison_read(self, temp_dir, small_dataset):
        """Compare read performance: Parquet vs CSV."""
        parquet_path = temp_dir / "test.parquet"
        csv_path = temp_dir / "test.csv"

        # Write files
        small_dataset.to_parquet(parquet_path, compression="snappy")
        small_dataset.to_csv(csv_path, index=False)

        # Measure Parquet read
        start = time.time()
        df_parquet = pd.read_parquet(parquet_path)
        parquet_time = time.time() - start

        # Measure CSV read
        start = time.time()
        df_csv = pd.read_csv(csv_path)
        csv_time = time.time() - start

        print(f"\nParquet read: {parquet_time:.4f}s")
        print(f"CSV read: {csv_time:.4f}s")

        assert len(df_parquet) == 1000
        assert len(df_csv) == 1000

    def test_compression_comparison(self, temp_dir, small_dataset):
        """Compare different compression algorithms."""
        compressions = ["none", "snappy", "gzip", "zstd"]
        results = {}

        for comp in compressions:
            path = temp_dir / f"test_{comp}.parquet"

            # Write with timing
            start = time.time()
            small_dataset.to_parquet(path, compression=comp if comp != "none" else None)
            write_time = time.time() - start

            # Read with timing
            start = time.time()
            pd.read_parquet(path)
            read_time = time.time() - start

            # Get file size
            file_size = path.stat().st_size

            results[comp] = {
                "write_time": write_time,
                "read_time": read_time,
                "file_size": file_size
            }

        # Print results
        print("\nCompression comparison:")
        for comp, metrics in results.items():
            print(f"{comp:10s}: write={metrics['write_time']:.4f}s, "
                  f"read={metrics['read_time']:.4f}s, "
                  f"size={metrics['file_size']:,} bytes")


class TestQueryPerformance:
    """Test query execution performance."""

    def test_simple_query_performance(self, temp_dir, medium_dataset):
        """Benchmark simple SELECT query."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create table and load data
        conn.execute("""
            CREATE TABLE data AS
            SELECT * FROM medium_dataset
        """)

        start = time.time()
        result = conn.execute("SELECT * FROM data WHERE value > 0").fetchall()
        elapsed = time.time() - start

        conn.close()

        print(f"\nSimple query (100K rows): {elapsed:.4f}s")
        assert len(result) > 0
        assert elapsed < 5.0

    def test_aggregate_query_performance(self, temp_dir, medium_dataset):
        """Benchmark aggregate query."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create table
        conn.execute("""
            CREATE TABLE data AS
            SELECT * FROM medium_dataset
        """)

        start = time.time()
        result = conn.execute("""
            SELECT category, COUNT(*) as count, AVG(value) as avg_value
            FROM data
            GROUP BY category
        """).fetchall()
        elapsed = time.time() - start

        conn.close()

        print(f"\nAggregate query (100K rows): {elapsed:.4f}s")
        assert len(result) > 0
        assert elapsed < 5.0

    def test_join_query_performance(self, temp_dir, small_dataset):
        """Benchmark JOIN query."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create tables
        conn.execute("CREATE TABLE t1 AS SELECT * FROM small_dataset")
        conn.execute("CREATE TABLE t2 AS SELECT id, category FROM small_dataset")

        start = time.time()
        result = conn.execute("""
            SELECT t1.*, t2.category as cat2
            FROM t1
            INNER JOIN t2 ON t1.id = t2.id
        """).fetchall()
        elapsed = time.time() - start

        conn.close()

        print(f"\nJOIN query (1K rows): {elapsed:.4f}s")
        assert len(result) == 1000
        assert elapsed < 2.0


class TestOptimizerPerformance:
    """Test query optimizer performance."""

    def test_optimizer_simple_query(self):
        """Benchmark optimizer on simple query."""
        optimizer = QueryOptimizer()
        query = "SELECT * FROM users WHERE age > 18 AND status = 'active'"

        start = time.time()
        result = optimizer.optimize(query)
        elapsed = time.time() - start

        print(f"\nOptimizer (simple query): {elapsed:.4f}s")
        assert result is not None
        assert elapsed < 1.0

    def test_optimizer_complex_query(self):
        """Benchmark optimizer on complex query."""
        optimizer = QueryOptimizer()
        query = """
            SELECT
                u.id, u.name, o.total, p.product_name
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            LEFT JOIN products p ON o.product_id = p.id
            WHERE u.age > 18
                AND o.status = 'completed'
                AND o.total > 100
            ORDER BY o.total DESC
            LIMIT 10
        """

        start = time.time()
        result = optimizer.optimize(query)
        elapsed = time.time() - start

        print(f"\nOptimizer (complex query): {elapsed:.4f}s")
        assert result is not None
        assert elapsed < 1.0


class TestCachePerformance:
    """Test cache performance."""

    def test_cache_put_performance(self):
        """Benchmark cache put operations."""
        cache = QueryCache(use_redis=False)

        data = {"result": list(range(1000))}

        start = time.time()
        for _ in range(100):
            key = cache.key_generator.generate(f"test query {_}")
            cache.put(key, data)
        elapsed = time.time() - start

        per_op = elapsed / 100
        print(f"\nCache PUT (100 ops): {elapsed:.4f}s ({per_op*1000:.2f}ms per op)")
        assert elapsed < 1.0

    def test_cache_get_performance(self):
        """Benchmark cache get operations."""
        cache = QueryCache(use_redis=False)

        # Pre-populate cache
        data = {"result": list(range(1000))}
        key = cache.key_generator.generate("test query")
        cache.put(key, data)

        start = time.time()
        for _ in range(100):
            result = cache.get(key)
        elapsed = time.time() - start

        per_op = elapsed / 100
        print(f"\nCache GET (100 ops): {elapsed:.4f}s ({per_op*1000:.2f}ms per op)")
        assert elapsed < 1.0

    def test_cache_hit_rate(self):
        """Test cache hit rate with repeated queries."""
        cache = QueryCache(use_redis=False)

        queries = [f"SELECT * FROM t{i}" for i in range(10)]
        data = {"result": list(range(100))}

        # Execute queries twice
        for _ in range(2):
            for query in queries:
                key = cache.key_generator.generate(query)

                if not cache.get(key):
                    cache.put(key, data)

        stats = cache.get_stats()

        # Check if stats has the expected structure
        if "metrics" in stats:
            metrics = stats["metrics"]
            hit_rate = (metrics["hits"] / metrics["total_requests"]) * 100
            print(f"\nCache hit rate: {hit_rate:.1f}%")
            assert hit_rate >= 50  # Should have some hits on second pass
        else:
            # Alternative stats structure
            print(f"\nCache stats: {stats}")
            assert stats["size"] > 0  # At least verify cache has entries


class TestConcurrentOperations:
    """Test concurrent operation performance."""

    def test_concurrent_queries(self, temp_dir, small_dataset):
        """Test concurrent query execution."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create table
        conn.execute("CREATE TABLE data AS SELECT * FROM small_dataset")
        conn.close()

        def run_query(query_id):
            conn = duckdb.connect(str(db_path))
            result = conn.execute("SELECT COUNT(*) FROM data WHERE value > 0").fetchall()
            conn.close()
            return query_id

        # Run 10 concurrent queries
        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_query, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]
        elapsed = time.time() - start

        print(f"\n10 concurrent queries: {elapsed:.2f}s ({10/elapsed:.1f} queries/sec)")
        assert len(results) == 10

    def test_concurrent_writes(self, temp_dir):
        """Test concurrent write operations."""

        def write_file(file_id):
            path = temp_dir / f"file_{file_id}.parquet"
            df = pd.DataFrame({
                "id": range(1000),
                "value": np.random.randn(1000)
            })
            df.to_parquet(path)
            return file_id

        # Write 10 files concurrently
        start = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_file, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]
        elapsed = time.time() - start

        print(f"\n10 concurrent writes: {elapsed:.2f}s")
        assert len(results) == 10


class TestMemoryUsage:
    """Test memory usage characteristics."""

    @pytest.mark.slow
    def test_large_dataset_memory(self, temp_dir, large_dataset):
        """Test memory efficiency with large dataset."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Measure initial memory
        initial_mem = process.memory_info().rss / 1024 / 1024  # MB

        # Write large file
        parquet_path = temp_dir / "large.parquet"
        large_dataset.to_parquet(parquet_path, compression="snappy")

        # Measure after write
        write_mem = process.memory_info().rss / 1024 / 1024  # MB

        # Read large file
        df = pd.read_parquet(parquet_path)

        # Measure after read
        read_mem = process.memory_info().rss / 1024 / 1024  # MB

        print(f"\nMemory usage:")
        print(f"  Initial: {initial_mem:.1f} MB")
        print(f"  After write: {write_mem:.1f} MB (+{write_mem - initial_mem:.1f} MB)")
        print(f"  After read: {read_mem:.1f} MB (+{read_mem - write_mem:.1f} MB)")

        # Cleanup
        del df


class TestThroughput:
    """Test throughput metrics."""

    def test_query_throughput(self, temp_dir, medium_dataset):
        """Measure query throughput (queries per second)."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        conn.execute("CREATE TABLE data AS SELECT * FROM medium_dataset")

        # Run queries for 5 seconds
        start = time.time()
        query_count = 0
        duration = 5.0

        while (time.time() - start) < duration:
            conn.execute("SELECT COUNT(*) FROM data WHERE value > 0").fetchall()
            query_count += 1

        elapsed = time.time() - start
        qps = query_count / elapsed

        conn.close()

        print(f"\nQuery throughput: {qps:.1f} queries/sec")
        print(f"Total queries in {duration}s: {query_count}")

    def test_write_throughput(self, temp_dir):
        """Measure write throughput (rows per second)."""
        total_rows = 10000

        df = pd.DataFrame({
            "id": range(total_rows),
            "value": np.random.randn(total_rows)
        })

        path = temp_dir / "throughput.parquet"

        start = time.time()
        df.to_parquet(path, compression="snappy")
        elapsed = time.time() - start

        rows_per_sec = total_rows / elapsed

        print(f"\nWrite throughput: {rows_per_sec:.0f} rows/sec")
        print(f"Total time for {total_rows} rows: {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--benchmark-only"])
