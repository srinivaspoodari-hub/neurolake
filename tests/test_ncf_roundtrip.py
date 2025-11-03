"""
Integration test for NCF write -> read roundtrip

Tests that data written to NCF format can be read back correctly.
"""

import numpy as np
import pandas as pd
import tempfile
import os
from pathlib import Path

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import (
    NCFSchema, ColumnSchema, NCFDataType, SemanticType
)


def test_basic_roundtrip():
    """Test basic write -> read roundtrip"""
    print("\n" + "=" * 60)
    print("TEST: Basic Roundtrip (write -> read)")
    print("=" * 60)

    # Create test data
    data = pd.DataFrame({
        "id": range(100),
        "value": np.random.rand(100),
    })

    print(f"[OK] Created test data: {data.shape}")

    # Create schema
    schema = NCFSchema(
        table_name="test_basic",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
        ]
    )

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        print(f"[OK] Writing to {tmp_path}...")
        with NCFWriter(tmp_path, schema, compression="zstd") as writer:
            writer.write(data)

        file_size = os.path.getsize(tmp_path)
        print(f"[OK] Wrote {len(data)} rows ({file_size:,} bytes)")

        # Read
        print(f"[OK] Reading from {tmp_path}...")
        with NCFReader(tmp_path) as reader:
            # Validate checksum
            assert reader.validate_checksum(), "Checksum validation failed"
            print(f"[OK] Checksum valid")

            # Read data
            result = reader.read()

        print(f"[OK] Read {len(result)} rows")

        # Verify
        assert len(result) == len(data), f"Row count mismatch: {len(result)} != {len(data)}"
        assert list(result.columns) == ["id", "value"], f"Column mismatch: {list(result.columns)}"

        # Check values
        assert np.array_equal(result["id"].values, data["id"].values), "ID column mismatch"
        assert np.allclose(result["value"].values, data["value"].values), "Value column mismatch"

        print(f"[OK] Data matches perfectly!")
        print(f"[PASS] TEST PASSED")

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_string_columns():
    """Test string column handling"""
    print("\n" + "=" * 60)
    print("TEST: String Columns")
    print("=" * 60)

    # Create test data with strings
    data = pd.DataFrame({
        "id": range(50),
        "name": [f"User_{i}" for i in range(50)],
        "email": [f"user{i}@example.com" for i in range(50)],
    })

    print(f"[OK] Created test data: {data.shape}")

    # Create schema
    schema = NCFSchema(
        table_name="test_strings",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ColumnSchema(name="email", data_type=NCFDataType.STRING, semantic_type=SemanticType.PII_EMAIL),
        ]
    )

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        print(f"[OK] Writing to {tmp_path}...")
        with NCFWriter(tmp_path, schema) as writer:
            writer.write(data)

        # Read
        print(f"[OK] Reading from {tmp_path}...")
        with NCFReader(tmp_path) as reader:
            result = reader.read()

        # Verify
        assert len(result) == len(data)
        assert list(result.columns) == ["id", "name", "email"]

        # Check string values
        assert list(result["name"]) == list(data["name"]), "Name column mismatch"
        assert list(result["email"]) == list(data["email"]), "Email column mismatch"

        print(f"[OK] String data matches!")
        print(f"[PASS] TEST PASSED")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_column_projection():
    """Test reading specific columns only"""
    print("\n" + "=" * 60)
    print("TEST: Column Projection (selective read)")
    print("=" * 60)

    # Create test data
    data = pd.DataFrame({
        "col1": range(100),
        "col2": range(100, 200),
        "col3": range(200, 300),
        "col4": range(300, 400),
    })

    print(f"[OK] Created test data: {data.shape}")

    # Create schema
    schema = NCFSchema(
        table_name="test_projection",
        columns=[
            ColumnSchema(name="col1", data_type=NCFDataType.INT64),
            ColumnSchema(name="col2", data_type=NCFDataType.INT64),
            ColumnSchema(name="col3", data_type=NCFDataType.INT64),
            ColumnSchema(name="col4", data_type=NCFDataType.INT64),
        ]
    )

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write all columns
        with NCFWriter(tmp_path, schema) as writer:
            writer.write(data)

        print(f"[OK] Wrote 4 columns")

        # Read only 2 columns
        print(f"[OK] Reading only col1 and col3...")
        with NCFReader(tmp_path) as reader:
            result = reader.read(columns=["col1", "col3"])

        # Verify
        assert len(result) == len(data)
        assert list(result.columns) == ["col1", "col3"], f"Got columns: {list(result.columns)}"

        # Check values
        assert np.array_equal(result["col1"].values, data["col1"].values)
        assert np.array_equal(result["col3"].values, data["col3"].values)

        print(f"[OK] Column projection works correctly!")
        print(f"[PASS] TEST PASSED")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_limit_rows():
    """Test reading limited number of rows"""
    print("\n" + "=" * 60)
    print("TEST: Row Limit")
    print("=" * 60)

    # Create test data
    data = pd.DataFrame({
        "id": range(1000),
        "value": np.random.rand(1000),
    })

    print(f"[OK] Created test data: {data.shape}")

    # Create schema
    schema = NCFSchema(
        table_name="test_limit",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
        ]
    )

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write 1000 rows
        with NCFWriter(tmp_path, schema) as writer:
            writer.write(data)

        print(f"[OK] Wrote 1000 rows")

        # Read only 10 rows
        print(f"[OK] Reading only first 10 rows...")
        with NCFReader(tmp_path) as reader:
            result = reader.read(limit=10)

        # Verify
        assert len(result) == 10, f"Expected 10 rows, got {len(result)}"
        assert np.array_equal(result["id"].values, data["id"].values[:10])

        print(f"[OK] Row limit works correctly!")
        print(f"[PASS] TEST PASSED")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_statistics():
    """Test statistics generation and retrieval"""
    print("\n" + "=" * 60)
    print("TEST: Statistics")
    print("=" * 60)

    # Create test data with known statistics
    data = pd.DataFrame({
        "id": range(1, 101),  # min=1, max=100
        "score": np.random.rand(100),  # min~0, max~1
    })

    print(f"[OK] Created test data: {data.shape}")

    # Create schema
    schema = NCFSchema(
        table_name="test_stats",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="score", data_type=NCFDataType.FLOAT64),
        ]
    )

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        with NCFWriter(tmp_path, schema) as writer:
            writer.write(data)

        # Read and check statistics
        print(f"[OK] Reading statistics...")
        with NCFReader(tmp_path) as reader:
            id_stats = reader.get_statistics("id")
            score_stats = reader.get_statistics("score")

        # Verify
        print(f"  ID stats: min={id_stats.min_value}, max={id_stats.max_value}")
        assert int(id_stats.min_value) == 1, f"Expected min=1, got {id_stats.min_value}"
        assert int(id_stats.max_value) == 100, f"Expected max=100, got {id_stats.max_value}"
        assert id_stats.null_count == 0, f"Expected null_count=0, got {id_stats.null_count}"
        assert id_stats.total_count == 100, f"Expected total_count=100, got {id_stats.total_count}"

        print(f"  Score stats: min={float(score_stats.min_value):.4f}, max={float(score_stats.max_value):.4f}")
        assert 0 <= float(score_stats.min_value) <= 1, f"Min value out of range: {score_stats.min_value}"
        assert 0 <= float(score_stats.max_value) <= 1, f"Max value out of range: {score_stats.max_value}"

        print(f"[OK] Statistics are correct!")
        print(f"[PASS] TEST PASSED")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_compression():
    """Test compression effectiveness"""
    print("\n" + "=" * 60)
    print("TEST: Compression")
    print("=" * 60)

    # Create test data with repeated values (compresses well)
    data = pd.DataFrame({
        "id": list(range(100)) * 10,  # Repeated 10 times
        "category": ["A", "B", "C", "D"] * 250,  # Repeated pattern
    })

    print(f"[OK] Created test data: {data.shape}")

    # Create schema
    schema = NCFSchema(
        table_name="test_compression",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="category", data_type=NCFDataType.STRING),
        ]
    )

    # Create temp files (compressed vs uncompressed)
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp1:
        compressed_path = tmp1.name

    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp2:
        uncompressed_path = tmp2.name

    try:
        # Write with compression
        print(f"[OK] Writing with ZSTD compression...")
        with NCFWriter(compressed_path, schema, compression="zstd") as writer:
            writer.write(data)

        compressed_size = os.path.getsize(compressed_path)
        print(f"  Compressed size: {compressed_size:,} bytes")

        # Write without compression
        print(f"[OK] Writing without compression...")
        with NCFWriter(uncompressed_path, schema, compression="none") as writer:
            writer.write(data)

        uncompressed_size = os.path.getsize(uncompressed_path)
        print(f"  Uncompressed size: {uncompressed_size:,} bytes")

        # Calculate compression ratio
        ratio = uncompressed_size / compressed_size
        print(f"  Compression ratio: {ratio:.2f}x")

        # Verify compression worked
        assert compressed_size < uncompressed_size, "Compression didn't reduce file size!"
        assert ratio > 2.0, f"Compression ratio too low: {ratio:.2f}x"

        # Verify both read correctly
        with NCFReader(compressed_path) as reader:
            result1 = reader.read()

        with NCFReader(uncompressed_path) as reader:
            result2 = reader.read()

        assert len(result1) == len(result2) == len(data)

        print(f"[OK] Compression works and data reads correctly!")
        print(f"[PASS] TEST PASSED")

    finally:
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
        if os.path.exists(uncompressed_path):
            os.remove(uncompressed_path)


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("NCF INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        test_basic_roundtrip,
        test_string_columns,
        test_column_projection,
        test_limit_rows,
        test_statistics,
        test_compression,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
