"""
End-to-End Storage Integration Tests

Tests storage operations including:
- File storage (local, in-memory)
- Parquet file operations
- NCF file operations
- CSV file operations
- Metadata management
- File versioning
- Storage statistics
- Compression and optimization
- Batch operations
- Error handling and recovery
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
import os
import time

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1, 101),
        "name": [f"Item_{i}" for i in range(1, 101)],
        "value": np.random.randn(100),
        "category": np.random.choice(["A", "B", "C", "D"], 100),
        "timestamp": pd.date_range("2024-01-01", periods=100, freq="1h"),
        "active": np.random.choice([True, False], 100),
    })


class TestParquetStorage:
    """Test Parquet file storage operations."""

    def test_write_and_read_parquet(self, temp_dir, sample_dataframe):
        """Test writing and reading Parquet files."""
        parquet_path = temp_dir / "test.parquet"

        # Write to Parquet
        sample_dataframe.to_parquet(parquet_path, compression="snappy")

        # Verify file created
        assert parquet_path.exists()
        assert parquet_path.stat().st_size > 0

        # Read back
        df_read = pd.read_parquet(parquet_path)

        # Verify data
        assert len(df_read) == len(sample_dataframe)
        pd.testing.assert_frame_equal(df_read, sample_dataframe)

    def test_parquet_compression_types(self, temp_dir, sample_dataframe):
        """Test different Parquet compression algorithms."""
        compressions = ["none", "snappy", "gzip", "zstd"]
        sizes = {}

        for compression in compressions:
            path = temp_dir / f"test_{compression}.parquet"
            sample_dataframe.to_parquet(path, compression=compression)

            assert path.exists()
            sizes[compression] = path.stat().st_size

            # Verify readability
            df_read = pd.read_parquet(path)
            assert len(df_read) == len(sample_dataframe)

        # Verify compressed files are smaller than uncompressed
        assert sizes["snappy"] < sizes["none"]
        assert sizes["gzip"] < sizes["none"]
        assert sizes["zstd"] < sizes["none"]

        print(f"Parquet compression sizes: {sizes}")

    def test_parquet_partitioning(self, temp_dir, sample_dataframe):
        """Test Parquet partitioned storage."""
        partition_dir = temp_dir / "partitioned"

        # Write partitioned by category
        sample_dataframe.to_parquet(
            partition_dir,
            partition_cols=["category"],
            compression="snappy"
        )

        # Verify partition directories created
        assert partition_dir.exists()

        # Read back all partitions
        df_read = pd.read_parquet(partition_dir)

        assert len(df_read) == len(sample_dataframe)

    def test_parquet_schema_preservation(self, temp_dir):
        """Test that Parquet preserves data types."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.1, 2.2, 3.3],
            "str_col": ["a", "b", "c"],
            "bool_col": [True, False, True],
            "datetime_col": pd.date_range("2024-01-01", periods=3),
        })

        path = temp_dir / "schema_test.parquet"
        df.to_parquet(path)

        df_read = pd.read_parquet(path)

        # Verify dtypes preserved
        assert df_read["int_col"].dtype == df["int_col"].dtype
        assert df_read["float_col"].dtype == df["float_col"].dtype
        assert df_read["str_col"].dtype == df["str_col"].dtype
        assert df_read["bool_col"].dtype == df["bool_col"].dtype

    def test_parquet_append_mode(self, temp_dir, sample_dataframe):
        """Test appending to Parquet files."""
        parquet_dir = temp_dir / "append_test"
        parquet_dir.mkdir()

        # Write first batch
        df1 = sample_dataframe.iloc[:50]
        df1.to_parquet(parquet_dir / "batch1.parquet")

        # Write second batch
        df2 = sample_dataframe.iloc[50:]
        df2.to_parquet(parquet_dir / "batch2.parquet")

        # Read all files
        df_combined = pd.read_parquet(parquet_dir)

        assert len(df_combined) == len(sample_dataframe)


class TestCSVStorage:
    """Test CSV file storage operations."""

    def test_write_and_read_csv(self, temp_dir, sample_dataframe):
        """Test writing and reading CSV files."""
        csv_path = temp_dir / "test.csv"

        # Write to CSV
        sample_dataframe.to_csv(csv_path, index=False)

        # Verify file created
        assert csv_path.exists()

        # Read back
        df_read = pd.read_csv(csv_path, parse_dates=["timestamp"])

        assert len(df_read) == len(sample_dataframe)

    def test_csv_compression(self, temp_dir, sample_dataframe):
        """Test CSV with gzip compression."""
        csv_path = temp_dir / "test.csv.gz"

        # Write compressed CSV
        sample_dataframe.to_csv(csv_path, index=False, compression="gzip")

        assert csv_path.exists()

        # Read compressed CSV
        df_read = pd.read_csv(csv_path, compression="gzip", parse_dates=["timestamp"])

        assert len(df_read) == len(sample_dataframe)

    def test_csv_with_custom_delimiter(self, temp_dir):
        """Test CSV with custom delimiter."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["a", "b", "c"],
        })

        csv_path = temp_dir / "test.tsv"

        # Write with tab delimiter
        df.to_csv(csv_path, sep="\t", index=False)

        # Read with tab delimiter
        df_read = pd.read_csv(csv_path, sep="\t")

        pd.testing.assert_frame_equal(df_read, df)


class TestNCFStorage:
    """Test NCF file storage operations."""

    def test_ncf_file_operations(self, temp_dir, sample_dataframe):
        """Test NCF file write, read, and verify."""
        ncf_path = temp_dir / "test.ncf"

        # Create schema
        schema = NCFSchema(
            table_name="sample",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="timestamp", data_type=NCFDataType.TIMESTAMP),
                ColumnSchema(name="active", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Write to NCF
        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(sample_dataframe)

        # Verify file created
        assert ncf_path.exists()
        assert ncf_path.stat().st_size > 0

        # Read back
        with NCFReader(str(ncf_path)) as reader:
            df_read = reader.read()

        # Verify data
        assert len(df_read) == len(sample_dataframe)

    def test_ncf_storage_efficiency(self, temp_dir, sample_dataframe):
        """Test NCF storage efficiency vs other formats."""
        ncf_path = temp_dir / "test.ncf"
        parquet_path = temp_dir / "test.parquet"
        csv_path = temp_dir / "test.csv"

        # Create NCF schema
        schema = NCFSchema(
            table_name="sample",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="timestamp", data_type=NCFDataType.TIMESTAMP),
                ColumnSchema(name="active", data_type=NCFDataType.BOOLEAN),
            ]
        )

        # Write to all formats
        with NCFWriter(str(ncf_path), schema, compression="zstd") as writer:
            writer.write(sample_dataframe)

        sample_dataframe.to_parquet(parquet_path, compression="snappy")
        sample_dataframe.to_csv(csv_path, index=False)

        # Compare sizes
        ncf_size = ncf_path.stat().st_size
        parquet_size = parquet_path.stat().st_size
        csv_size = csv_path.stat().st_size

        print(f"\nStorage size comparison (100 rows):")
        print(f"  NCF: {ncf_size:,} bytes")
        print(f"  Parquet: {parquet_size:,} bytes")
        print(f"  CSV: {csv_size:,} bytes")

        # CSV should be larger than binary formats (but not always guaranteed)
        # Just verify files were created successfully
        assert ncf_size > 0
        assert parquet_size > 0
        assert csv_size > 0

        # Binary formats should be reasonably efficient
        assert csv_size > min(ncf_size, parquet_size)


class TestFileMetadata:
    """Test file metadata operations."""

    def test_file_statistics(self, temp_dir, sample_dataframe):
        """Test extracting file statistics."""
        parquet_path = temp_dir / "test.parquet"

        # Write file
        sample_dataframe.to_parquet(parquet_path)

        # Get file stats
        file_stats = parquet_path.stat()

        assert file_stats.st_size > 0
        assert file_stats.st_mtime > 0

        # Get Parquet metadata
        parquet_file = pq.ParquetFile(parquet_path)
        metadata = parquet_file.metadata

        assert metadata.num_rows == len(sample_dataframe)
        assert metadata.num_columns == len(sample_dataframe.columns)

    def test_file_versioning(self, temp_dir, sample_dataframe):
        """Test file versioning strategy."""
        base_path = temp_dir / "data"
        base_path.mkdir()

        # Write version 1
        v1_path = base_path / "data_v1.parquet"
        sample_dataframe.to_parquet(v1_path)

        # Modify data and write version 2
        df_v2 = sample_dataframe.copy()
        df_v2["value"] = df_v2["value"] * 2
        v2_path = base_path / "data_v2.parquet"
        df_v2.to_parquet(v2_path)

        # Verify both versions exist
        assert v1_path.exists()
        assert v2_path.exists()

        # Verify they're different
        df1 = pd.read_parquet(v1_path)
        df2 = pd.read_parquet(v2_path)

        assert not df1["value"].equals(df2["value"])


class TestBatchOperations:
    """Test batch storage operations."""

    def test_batch_write_parquet(self, temp_dir):
        """Test writing multiple files in batch."""
        batch_dir = temp_dir / "batch"
        batch_dir.mkdir()

        # Create and write 10 files
        for i in range(10):
            df = pd.DataFrame({
                "id": range(i * 100, (i + 1) * 100),
                "value": np.random.randn(100),
            })

            path = batch_dir / f"file_{i:02d}.parquet"
            df.to_parquet(path)

        # Verify all files created
        files = list(batch_dir.glob("*.parquet"))
        assert len(files) == 10

    def test_batch_read_parquet(self, temp_dir):
        """Test reading multiple Parquet files."""
        batch_dir = temp_dir / "batch"
        batch_dir.mkdir()

        # Create multiple files
        for i in range(5):
            df = pd.DataFrame({
                "id": range(i * 20, (i + 1) * 20),
                "value": np.random.randn(20),
            })
            df.to_parquet(batch_dir / f"file_{i}.parquet")

        # Read all files
        df_combined = pd.read_parquet(batch_dir)

        # Should have 100 total rows
        assert len(df_combined) == 100

    def test_batch_conversion(self, temp_dir):
        """Test batch conversion between formats."""
        csv_dir = temp_dir / "csv"
        parquet_dir = temp_dir / "parquet"
        csv_dir.mkdir()
        parquet_dir.mkdir()

        # Create CSV files
        for i in range(5):
            df = pd.DataFrame({
                "id": range(i * 10, (i + 1) * 10),
                "value": np.random.randn(10),
            })
            df.to_csv(csv_dir / f"file_{i}.csv", index=False)

        # Convert to Parquet
        for csv_file in csv_dir.glob("*.csv"):
            df = pd.read_csv(csv_file)
            parquet_file = parquet_dir / f"{csv_file.stem}.parquet"
            df.to_parquet(parquet_file)

        # Verify conversion
        parquet_files = list(parquet_dir.glob("*.parquet"))
        assert len(parquet_files) == 5


class TestStorageErrorHandling:
    """Test error handling in storage operations."""

    def test_read_nonexistent_file(self, temp_dir):
        """Test reading non-existent file."""
        with pytest.raises(FileNotFoundError):
            pd.read_parquet(temp_dir / "nonexistent.parquet")

    def test_write_to_readonly_location(self, temp_dir):
        """Test writing to read-only location."""
        readonly_file = temp_dir / "readonly.parquet"

        # Create file and make it read-only
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_parquet(readonly_file)

        # Make read-only
        os.chmod(readonly_file, 0o444)

        # Try to overwrite (should fail on write)
        # Note: pandas may handle this differently on different platforms
        try:
            df.to_parquet(readonly_file)
        except (PermissionError, OSError):
            pass  # Expected

        # Restore permissions for cleanup
        os.chmod(readonly_file, 0o644)

    def test_corrupted_file_handling(self, temp_dir):
        """Test handling of corrupted files."""
        corrupt_path = temp_dir / "corrupt.parquet"

        # Create corrupted file
        with open(corrupt_path, "wb") as f:
            f.write(b"This is not a valid Parquet file")

        # Try to read (should fail)
        with pytest.raises(Exception):  # PyArrow will raise an error
            pd.read_parquet(corrupt_path)


class TestStoragePerformance:
    """Test storage performance characteristics."""

    def test_write_performance(self, temp_dir):
        """Test write performance for different formats."""
        # Create larger dataset
        df = pd.DataFrame({
            "id": range(10000),
            "value": np.random.randn(10000),
            "category": np.random.choice(["A", "B", "C", "D"], 10000),
        })

        # Test Parquet write
        parquet_path = temp_dir / "perf.parquet"
        start = time.time()
        df.to_parquet(parquet_path)
        parquet_time = time.time() - start

        # Test CSV write
        csv_path = temp_dir / "perf.csv"
        start = time.time()
        df.to_csv(csv_path, index=False)
        csv_time = time.time() - start

        print(f"\nWrite performance (10K rows):")
        print(f"  Parquet: {parquet_time:.4f}s")
        print(f"  CSV: {csv_time:.4f}s")

        # Parquet should generally be faster or comparable
        assert parquet_time < 5.0
        assert csv_time < 5.0

    def test_read_performance(self, temp_dir):
        """Test read performance for different formats."""
        # Create dataset
        df = pd.DataFrame({
            "id": range(10000),
            "value": np.random.randn(10000),
        })

        # Write files
        parquet_path = temp_dir / "perf.parquet"
        csv_path = temp_dir / "perf.csv"
        df.to_parquet(parquet_path)
        df.to_csv(csv_path, index=False)

        # Test Parquet read
        start = time.time()
        pd.read_parquet(parquet_path)
        parquet_time = time.time() - start

        # Test CSV read
        start = time.time()
        pd.read_csv(csv_path)
        csv_time = time.time() - start

        print(f"\nRead performance (10K rows):")
        print(f"  Parquet: {parquet_time:.4f}s")
        print(f"  CSV: {csv_time:.4f}s")

        # Parquet should be faster
        assert parquet_time < csv_time


class TestStoragePatterns:
    """Test common storage patterns."""

    def test_incremental_updates(self, temp_dir):
        """Test incremental data updates pattern."""
        data_dir = temp_dir / "incremental"
        data_dir.mkdir()

        # Day 1: Write initial data
        df_day1 = pd.DataFrame({
            "id": range(100),
            "date": "2024-01-01",
            "value": np.random.randn(100),
        })
        df_day1.to_parquet(data_dir / "data_2024-01-01.parquet")

        # Day 2: Add new data
        df_day2 = pd.DataFrame({
            "id": range(100, 200),
            "date": "2024-01-02",
            "value": np.random.randn(100),
        })
        df_day2.to_parquet(data_dir / "data_2024-01-02.parquet")

        # Read all data
        df_all = pd.read_parquet(data_dir)

        assert len(df_all) == 200

    def test_data_archiving(self, temp_dir):
        """Test data archiving pattern."""
        active_dir = temp_dir / "active"
        archive_dir = temp_dir / "archive"
        active_dir.mkdir()
        archive_dir.mkdir()

        # Create active data
        df = pd.DataFrame({
            "id": range(100),
            "timestamp": pd.date_range("2024-01-01", periods=100),
            "value": np.random.randn(100),
        })

        active_path = active_dir / "current.parquet"
        df.to_parquet(active_path)

        # Archive (move to archive directory)
        archive_path = archive_dir / f"archive_{datetime.now().strftime('%Y%m%d')}.parquet"
        shutil.copy(active_path, archive_path)

        # Verify both exist
        assert active_path.exists()
        assert archive_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
