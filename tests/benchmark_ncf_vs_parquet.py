"""
Benchmark NCF vs Parquet

Compares performance metrics between NCF and Parquet formats:
- File size / compression ratio
- Write speed
- Read speed
- Memory usage

Run: python tests/benchmark_ncf_vs_parquet.py
"""

import numpy as np
import pandas as pd
import tempfile
import os
import time
import psutil
from pathlib import Path

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import (
    NCFSchema, ColumnSchema, NCFDataType, SemanticType
)


def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def create_test_dataset(num_rows=100_000):
    """Create a test dataset with mixed data types"""
    print(f"\nCreating test dataset with {num_rows:,} rows...")

    data = pd.DataFrame({
        "id": range(num_rows),
        "value": np.random.rand(num_rows),
        "category": np.random.choice(["A", "B", "C", "D", "E"], num_rows),
        "score": np.random.randint(0, 100, num_rows),
        "name": [f"User_{i}" for i in range(num_rows)],
        "email": [f"user{i}@example.com" for i in range(num_rows)],
    })

    print(f"Dataset shape: {data.shape}")
    print(f"Dataset memory: {data.memory_usage(deep=True).sum() / (1024*1024):.2f} MB")

    return data


def benchmark_ncf_write(data):
    """Benchmark NCF write performance"""
    print("\n" + "=" * 60)
    print("NCF WRITE BENCHMARK")
    print("=" * 60)

    # Create schema
    schema = NCFSchema(
        table_name="benchmark",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
            ColumnSchema(name="category", data_type=NCFDataType.STRING),
            ColumnSchema(name="score", data_type=NCFDataType.INT64),
            ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ColumnSchema(name="email", data_type=NCFDataType.STRING, semantic_type=SemanticType.PII_EMAIL),
        ]
    )

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Benchmark write
        mem_before = get_memory_usage()
        start_time = time.time()

        with NCFWriter(tmp_path, schema, compression="zstd") as writer:
            writer.write(data)

        write_time = time.time() - start_time
        mem_after = get_memory_usage()
        file_size = os.path.getsize(tmp_path)

        print(f"Write time: {write_time:.4f} seconds")
        print(f"Write speed: {len(data) / write_time:,.0f} rows/sec")
        print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
        print(f"Memory delta: {mem_after - mem_before:.2f} MB")

        return {
            "write_time": write_time,
            "write_speed": len(data) / write_time,
            "file_size": file_size,
            "file_path": tmp_path,
            "memory_delta": mem_after - mem_before,
        }

    except Exception as e:
        print(f"ERROR: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def benchmark_ncf_read(ncf_results):
    """Benchmark NCF read performance"""
    print("\n" + "=" * 60)
    print("NCF READ BENCHMARK")
    print("=" * 60)

    tmp_path = ncf_results["file_path"]

    try:
        # Benchmark full read
        mem_before = get_memory_usage()
        start_time = time.time()

        with NCFReader(tmp_path) as reader:
            data = reader.read()

        read_time = time.time() - start_time
        mem_after = get_memory_usage()

        print(f"Read time: {read_time:.4f} seconds")
        print(f"Read speed: {len(data) / read_time:,.0f} rows/sec")
        print(f"Rows read: {len(data):,}")
        print(f"Memory delta: {mem_after - mem_before:.2f} MB")

        ncf_results["read_time"] = read_time
        ncf_results["read_speed"] = len(data) / read_time
        ncf_results["read_memory_delta"] = mem_after - mem_before

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def benchmark_parquet_write(data):
    """Benchmark Parquet write performance"""
    print("\n" + "=" * 60)
    print("PARQUET WRITE BENCHMARK")
    print("=" * 60)

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Benchmark write
        mem_before = get_memory_usage()
        start_time = time.time()

        data.to_parquet(tmp_path, compression="snappy", index=False)

        write_time = time.time() - start_time
        mem_after = get_memory_usage()
        file_size = os.path.getsize(tmp_path)

        print(f"Write time: {write_time:.4f} seconds")
        print(f"Write speed: {len(data) / write_time:,.0f} rows/sec")
        print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
        print(f"Memory delta: {mem_after - mem_before:.2f} MB")

        return {
            "write_time": write_time,
            "write_speed": len(data) / write_time,
            "file_size": file_size,
            "file_path": tmp_path,
            "memory_delta": mem_after - mem_before,
        }

    except Exception as e:
        print(f"ERROR: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def benchmark_parquet_read(parquet_results):
    """Benchmark Parquet read performance"""
    print("\n" + "=" * 60)
    print("PARQUET READ BENCHMARK")
    print("=" * 60)

    tmp_path = parquet_results["file_path"]

    try:
        # Benchmark full read
        mem_before = get_memory_usage()
        start_time = time.time()

        data = pd.read_parquet(tmp_path)

        read_time = time.time() - start_time
        mem_after = get_memory_usage()

        print(f"Read time: {read_time:.4f} seconds")
        print(f"Read speed: {len(data) / read_time:,.0f} rows/sec")
        print(f"Rows read: {len(data):,}")
        print(f"Memory delta: {mem_after - mem_before:.2f} MB")

        parquet_results["read_time"] = read_time
        parquet_results["read_speed"] = len(data) / read_time
        parquet_results["read_memory_delta"] = mem_after - mem_before

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def print_comparison(ncf_results, parquet_results):
    """Print comparison table"""
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    print("\nFILE SIZE:")
    print(f"  NCF:     {ncf_results['file_size']:>12,} bytes ({ncf_results['file_size']/(1024*1024):>6.2f} MB)")
    print(f"  Parquet: {parquet_results['file_size']:>12,} bytes ({parquet_results['file_size']/(1024*1024):>6.2f} MB)")
    compression_ratio = parquet_results['file_size'] / ncf_results['file_size']
    print(f"  NCF is {compression_ratio:.2f}x {'smaller' if compression_ratio > 1 else 'larger'} than Parquet")

    print("\nWRITE PERFORMANCE:")
    print(f"  NCF:     {ncf_results['write_time']:>8.4f} sec  ({ncf_results['write_speed']:>10,.0f} rows/sec)")
    print(f"  Parquet: {parquet_results['write_time']:>8.4f} sec  ({parquet_results['write_speed']:>10,.0f} rows/sec)")
    write_speedup = ncf_results['write_speed'] / parquet_results['write_speed']
    print(f"  NCF is {write_speedup:.2f}x {'faster' if write_speedup > 1 else 'slower'} than Parquet")

    print("\nREAD PERFORMANCE:")
    print(f"  NCF:     {ncf_results['read_time']:>8.4f} sec  ({ncf_results['read_speed']:>10,.0f} rows/sec)")
    print(f"  Parquet: {parquet_results['read_time']:>8.4f} sec  ({parquet_results['read_speed']:>10,.0f} rows/sec)")
    read_speedup = ncf_results['read_speed'] / parquet_results['read_speed']
    print(f"  NCF is {read_speedup:.2f}x {'faster' if read_speedup > 1 else 'slower'} than Parquet")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Determine winner
    ncf_score = 0
    parquet_score = 0

    if compression_ratio > 1:
        ncf_score += 1
    else:
        parquet_score += 1

    if write_speedup > 1:
        ncf_score += 1
    else:
        parquet_score += 1

    if read_speedup > 1:
        ncf_score += 1
    else:
        parquet_score += 1

    print(f"NCF wins: {ncf_score}/3 categories")
    print(f"Parquet wins: {parquet_score}/3 categories")

    if ncf_score > parquet_score:
        print("\n[RESULT] NCF outperforms Parquet overall!")
    elif parquet_score > ncf_score:
        print("\n[RESULT] Parquet outperforms NCF overall (but NCF is still in early development)")
    else:
        print("\n[RESULT] NCF and Parquet are comparable!")


def run_benchmark(num_rows=100_000):
    """Run full benchmark suite"""
    print("=" * 60)
    print("NCF vs PARQUET BENCHMARK")
    print("=" * 60)
    print(f"Dataset size: {num_rows:,} rows")

    # Create test data
    data = create_test_dataset(num_rows)

    # Benchmark NCF
    ncf_results = benchmark_ncf_write(data)
    benchmark_ncf_read(ncf_results)

    # Benchmark Parquet
    parquet_results = benchmark_parquet_write(data)
    benchmark_parquet_read(parquet_results)

    # Print comparison
    print_comparison(ncf_results, parquet_results)


if __name__ == "__main__":
    import sys

    # Default to 100k rows
    num_rows = 100_000

    if len(sys.argv) > 1:
        num_rows = int(sys.argv[1])

    run_benchmark(num_rows)
