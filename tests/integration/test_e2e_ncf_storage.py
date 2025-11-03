"""
End-to-End NCF Storage Integration Tests

Tests the complete NCF (Neural Compression Format) storage pipeline including:
- Writing data to NCF format
- Reading data from NCF format
- Query execution on NCF-stored data
- Compression effectiveness
- Data integrity and roundtrip testing
- Performance benchmarking
- Integration with query engine
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
import duckdb
import time
import os

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType
from neurolake.optimizer.optimizer import QueryOptimizer
from neurolake.cache.cache import QueryCache


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "age": [30, 25, 35, 28, 32],
        "salary": [75000.0, 65000.0, 85000.0, 70000.0, 80000.0],
        "department": ["Engineering", "Sales", "Engineering", "Marketing", "Sales"],
    })


@pytest.fixture
def large_dataframe():
    """Create larger DataFrame for performance testing."""
    np.random.seed(42)
    n_rows = 10000

    return pd.DataFrame({
        "id": range(n_rows),
        "value": np.random.randn(n_rows),
        "category": np.random.choice(["A", "B", "C", "D"], n_rows),
        "flag": np.random.choice([True, False], n_rows),
    })


class TestNCFWriteRead:
    """Test NCF write and read operations."""

    def test_write_and_read_basic(self, temp_dir, sample_dataframe):
        """Test basic NCF write and read."""
        ncf_path = temp_dir / "test.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="sample",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="age", data_type=NCFDataType.INT64),
                ColumnSchema(name="salary", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="department", data_type=NCFDataType.STRING),
            ]
        )

        # Write DataFrame to NCF using context manager
        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(sample_dataframe)

        # Verify file was created
        assert ncf_path.exists()
        assert ncf_path.stat().st_size > 0

        # Read back from NCF using context manager
        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        # Verify data integrity
        assert df_read is not None
        assert len(df_read) == len(sample_dataframe)
        assert list(df_read.columns) == list(sample_dataframe.columns)

        # Verify values
        pd.testing.assert_frame_equal(df_read, sample_dataframe)

    def test_ncf_roundtrip_with_various_types(self, temp_dir):
        """Test NCF roundtrip with various data types."""
        # Create DataFrame with various types
        df = pd.DataFrame({
            "int_col": [1, 2, 3, 4, 5],
            "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
            "str_col": ["a", "b", "c", "d", "e"],
            "bool_col": [True, False, True, False, True],
        })

        ncf_path = temp_dir / "types.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="types",
            columns=[
                ColumnSchema(name="int_col", data_type=NCFDataType.INT64),
                ColumnSchema(name="float_col", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="str_col", data_type=NCFDataType.STRING),
                ColumnSchema(name="bool_col", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Write
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(df)

        # Read
        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        # Verify
        assert df_read is not None
        assert len(df_read) == len(df)
        pd.testing.assert_frame_equal(df_read, df)

    def test_ncf_with_null_values(self, temp_dir):
        """Test NCF handling of NULL values."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "value": [10.0, None, 30.0, None, 50.0],
            "name": ["Alice", None, "Charlie", "Diana", None],
        })

        ncf_path = temp_dir / "nulls.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="nulls",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ]
        )

        # Write
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(df)

        # Read
        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        # Verify NULL handling
        assert df_read is not None
        assert df_read["value"].isna().sum() == 2
        assert df_read["name"].isna().sum() == 2
        pd.testing.assert_frame_equal(df_read, df)


class TestNCFQueryExecution:
    """Test query execution on NCF-stored data."""

    def test_query_ncf_data_with_duckdb(self, temp_dir, sample_dataframe):
        """Test executing queries on NCF data using DuckDB."""
        ncf_path = temp_dir / "employees.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="employees",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="age", data_type=NCFDataType.INT64),
                ColumnSchema(name="salary", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="department", data_type=NCFDataType.STRING),
            ]
        )

        # Write data to NCF
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(sample_dataframe)

        # Read NCF data
        with NCFReader(str(ncf_path)) as reader:
            df = reader.read()

        # Create DuckDB connection and load data
        conn = duckdb.connect()
        conn.register("employees", df)

        # Execute queries
        result = conn.execute("SELECT * FROM employees WHERE age > 28").fetchdf()
        assert len(result) == 3  # Alice (30), Charlie (35), Eve (32)

        result = conn.execute("SELECT department, AVG(salary) as avg_sal FROM employees GROUP BY department").fetchdf()
        assert len(result) == 3  # Engineering, Sales, Marketing

        conn.close()

    def test_query_with_optimization(self, temp_dir, sample_dataframe):
        """Test optimized queries on NCF data."""
        ncf_path = temp_dir / "data.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="data",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="age", data_type=NCFDataType.INT64),
                ColumnSchema(name="salary", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="department", data_type=NCFDataType.STRING),
            ]
        )

        # Write to NCF
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(sample_dataframe)

        # Read from NCF
        with NCFReader(str(ncf_path)) as reader:
            df = reader.read()

        # Setup query execution
        conn = duckdb.connect()
        conn.register("data", df)

        optimizer = QueryOptimizer()

        # Test query optimization
        sql = "SELECT * FROM data WHERE age > 25"
        optimized_sql = optimizer.optimize(sql)

        assert optimized_sql is not None

        # Execute optimized query
        result = conn.execute(optimized_sql).fetchdf()
        assert len(result) > 0

        conn.close()

    def test_query_with_cache(self, temp_dir, sample_dataframe):
        """Test cached queries on NCF data."""
        ncf_path = temp_dir / "cached.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="cached",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="age", data_type=NCFDataType.INT64),
                ColumnSchema(name="salary", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="department", data_type=NCFDataType.STRING),
            ]
        )

        # Write to NCF
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(sample_dataframe)

        # Read from NCF
        with NCFReader(str(ncf_path)) as reader:
            df = reader.read()

        # Setup
        conn = duckdb.connect()
        conn.register("cached", df)
        cache = QueryCache(use_redis=False)

        sql = "SELECT * FROM cached WHERE department = 'Engineering'"

        # First execution - cache miss
        cache_key = cache.key_generator.generate(sql)
        cached = cache.get(cache_key)
        assert cached is None

        # Execute query
        result = conn.execute(sql).fetchdf()
        result_list = result.values.tolist()

        # Cache result
        cache.put(cache_key, result_list)

        # Second execution - cache hit
        cached = cache.get(cache_key)
        assert cached is not None
        assert len(cached) == 2  # Alice and Charlie

        conn.close()


class TestNCFCompression:
    """Test NCF compression effectiveness."""

    def test_compression_ratio(self, temp_dir, large_dataframe):
        """Test NCF compression ratio."""
        ncf_path = temp_dir / "compressed.ncf"
        parquet_path = temp_dir / "uncompressed.parquet"

        # Define schema for NCF
        schema = NCFSchema(
            table_name="large",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="flag", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Write to NCF (with compression)
        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(large_dataframe)

        # Write to Parquet (for comparison)
        large_dataframe.to_parquet(parquet_path, compression="none")

        # Compare file sizes
        ncf_size = ncf_path.stat().st_size
        parquet_size = parquet_path.stat().st_size

        # NCF should be smaller (or at least not significantly larger)
        assert ncf_size > 0
        assert parquet_size > 0

        compression_ratio = ncf_size / parquet_size
        print(f"NCF compression ratio: {compression_ratio:.2%}")

        # Verify we can read compressed data
        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        assert len(df_read) == len(large_dataframe)

    def test_different_compression_levels(self, temp_dir, sample_dataframe):
        """Test different compression algorithms."""
        compression_algos = ["none", "zstd"]
        sizes = {}

        # Define schema
        schema = NCFSchema(
            table_name="sample",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="age", data_type=NCFDataType.INT64),
                ColumnSchema(name="salary", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="department", data_type=NCFDataType.STRING),
            ]
        )

        for algo in compression_algos:
            ncf_path = temp_dir / f"compressed_{algo}.ncf"

            with NCFWriter(str(ncf_path), schema, compression=algo) as writer:
                writer.write(sample_dataframe)

            sizes[algo] = ncf_path.stat().st_size

            # Verify readability
            with NCFReader(str(ncf_path)) as reader:
                df_read = reader.read()

            pd.testing.assert_frame_equal(df_read, sample_dataframe)

        # Verify compression actually reduces size (or at least doesn't increase)
        print(f"Uncompressed: {sizes['none']} bytes, Compressed: {sizes['zstd']} bytes")
        assert sizes['zstd'] <= sizes['none']


class TestNCFPerformance:
    """Test NCF performance benchmarks."""

    def test_write_performance(self, temp_dir, large_dataframe):
        """Test NCF write performance."""
        ncf_path = temp_dir / "perf_write.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="perf",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="flag", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Benchmark write
        start = time.time()
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(large_dataframe)
        write_time = time.time() - start

        print(f"NCF write time for {len(large_dataframe)} rows: {write_time:.3f}s")

        # Should complete in reasonable time (< 10 seconds for 10k rows)
        assert write_time < 10.0
        assert ncf_path.exists()

    def test_read_performance(self, temp_dir, large_dataframe):
        """Test NCF read performance."""
        ncf_path = temp_dir / "perf_read.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="perf",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="flag", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Write data first
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(large_dataframe)

        # Benchmark read
        start = time.time()
        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()
        read_time = time.time() - start

        print(f"NCF read time for {len(large_dataframe)} rows: {read_time:.3f}s")

        # Should complete in reasonable time
        assert read_time < 10.0
        assert len(df_read) == len(large_dataframe)

    @pytest.mark.slow
    def test_ncf_vs_parquet_performance(self, temp_dir, large_dataframe):
        """Compare NCF vs Parquet performance."""
        ncf_path = temp_dir / "perf.ncf"
        parquet_path = temp_dir / "perf.parquet"

        # Define schema for NCF
        schema = NCFSchema(
            table_name="perf",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="flag", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Write NCF
        start = time.time()
        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(large_dataframe)
        ncf_write_time = time.time() - start

        # Write Parquet
        start = time.time()
        large_dataframe.to_parquet(parquet_path)
        parquet_write_time = time.time() - start

        # Read NCF
        start = time.time()
        with NCFReader(str(ncf_path)) as reader:
            ncf_df = reader.read()
        ncf_read_time = time.time() - start

        # Read Parquet
        start = time.time()
        parquet_df = pd.read_parquet(parquet_path)
        parquet_read_time = time.time() - start

        # Print comparison
        print(f"\nPerformance Comparison ({len(large_dataframe)} rows):")
        print(f"NCF Write: {ncf_write_time:.3f}s, Read: {ncf_read_time:.3f}s")
        print(f"Parquet Write: {parquet_write_time:.3f}s, Read: {parquet_read_time:.3f}s")
        print(f"NCF Size: {ncf_path.stat().st_size / 1024:.1f} KB")
        print(f"Parquet Size: {parquet_path.stat().st_size / 1024:.1f} KB")

        # Verify correctness
        assert len(ncf_df) == len(parquet_df)


class TestNCFDataIntegrity:
    """Test NCF data integrity and edge cases."""

    def test_empty_dataframe(self, temp_dir):
        """Test NCF with empty DataFrame."""
        df = pd.DataFrame(columns=["id", "name", "value"])

        ncf_path = temp_dir / "empty.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="empty",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
            ]
        )

        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(df)

        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        assert len(df_read) == 0
        assert list(df_read.columns) == list(df.columns)

    def test_large_strings(self, temp_dir):
        """Test NCF with large string values."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "large_text": [
                "A" * 10000,
                "B" * 10000,
                "C" * 10000,
            ]
        })

        ncf_path = temp_dir / "large_strings.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="large_strings",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="large_text", data_type=NCFDataType.STRING),
            ]
        )

        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(df)

        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        pd.testing.assert_frame_equal(df_read, df)

    def test_numeric_precision(self, temp_dir):
        """Test NCF numeric precision."""
        df = pd.DataFrame({
            "int64_max": [np.iinfo(np.int64).max],
            "int64_min": [np.iinfo(np.int64).min],
            "float64_small": [1e-308],
            "float64_large": [1e308],
        })

        ncf_path = temp_dir / "precision.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="precision",
            columns=[
                ColumnSchema(name="int64_max", data_type=NCFDataType.INT64),
                ColumnSchema(name="int64_min", data_type=NCFDataType.INT64),
                ColumnSchema(name="float64_small", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="float64_large", data_type=NCFDataType.FLOAT64),
            ]
        )

        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(df)

        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        # Verify numeric precision
        assert df_read["int64_max"].iloc[0] == df["int64_max"].iloc[0]
        assert df_read["int64_min"].iloc[0] == df["int64_min"].iloc[0]
        np.testing.assert_almost_equal(
            df_read["float64_small"].iloc[0],
            df["float64_small"].iloc[0]
        )

    def test_special_characters(self, temp_dir):
        """Test NCF with special characters in strings."""
        df = pd.DataFrame({
            "text": [
                "Hello, 世界!",
                "Emoji: 😀🎉",
                "Special: \n\t\r",
                "Quotes: \"'`",
            ]
        })

        ncf_path = temp_dir / "special_chars.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="special_chars",
            columns=[
                ColumnSchema(name="text", data_type=NCFDataType.STRING),
            ]
        )

        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(df)

        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        pd.testing.assert_frame_equal(df_read, df)


class TestNCFIntegrationWithPipeline:
    """Test NCF integration with complete data pipeline."""

    def test_etl_pipeline_with_ncf_storage(self, temp_dir):
        """Test complete ETL pipeline using NCF for storage."""
        # 1. EXTRACT: Create source data
        source_df = pd.DataFrame({
            "id": range(1, 101),
            "value": np.random.randn(100),
            "category": np.random.choice(["A", "B", "C"], 100),
        })

        # 2. TRANSFORM: Filter and aggregate
        transformed_df = source_df[source_df["value"] > 0].copy()

        # 3. LOAD: Store in NCF
        ncf_path = temp_dir / "pipeline_output.ncf"

        # Define schema
        schema = NCFSchema(
            table_name="pipeline_output",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
            ]
        )

        with NCFWriter(str(ncf_path), schema) as writer:
            writer.write(transformed_df)

        # 4. VERIFY: Read back and query
        with NCFReader(str(ncf_path)) as reader:
            df_stored = reader.read()

        conn = duckdb.connect()
        conn.register("pipeline_data", df_stored)

        result = conn.execute("""
            SELECT category, COUNT(*) as count, AVG(value) as avg_value
            FROM pipeline_data
            GROUP BY category
        """).fetchdf()

        assert len(result) > 0
        assert "avg_value" in result.columns

        conn.close()

    def test_multi_file_ncf_storage(self, temp_dir):
        """Test storing multiple datasets in NCF."""
        datasets = {
            "users": pd.DataFrame({
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
            }),
            "orders": pd.DataFrame({
                "id": [101, 102, 103],
                "user_id": [1, 2, 1],
                "amount": [100.0, 200.0, 150.0],
            }),
        }

        # Write multiple datasets
        users_schema = NCFSchema(
            table_name="users",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ]
        )

        orders_schema = NCFSchema(
            table_name="orders",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="user_id", data_type=NCFDataType.INT64),
                ColumnSchema(name="amount", data_type=NCFDataType.FLOAT64),
            ]
        )

        # Write users
        with NCFWriter(str(temp_dir / "users.ncf"), users_schema) as writer:
            writer.write(datasets["users"])

        # Write orders
        with NCFWriter(str(temp_dir / "orders.ncf"), orders_schema) as writer:
            writer.write(datasets["orders"])

        # Read and join
        with NCFReader(str(temp_dir / "users.ncf")) as reader:
            users_df = reader.read()

        with NCFReader(str(temp_dir / "orders.ncf")) as reader:
            orders_df = reader.read()

        # Execute join query
        conn = duckdb.connect()
        conn.register("users", users_df)
        conn.register("orders", orders_df)

        result = conn.execute("""
            SELECT u.name, COUNT(o.id) as order_count, SUM(o.amount) as total_amount
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.name
            ORDER BY total_amount DESC
        """).fetchdf()

        assert len(result) == 3
        assert result["order_count"].sum() == 3

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
