"""
Benchmark: Rust vs Python NCF Implementations

Compares performance of:
- Python v1.1 (optimized)
- Rust v2.0 (native)
- Apache Parquet (baseline)

Requirements:
    1. Rust installed and built: cd core/ncf-rust && maturin develop --release
    2. Python packages: pandas, pyarrow

Usage:
    python tests/benchmark_rust_vs_python.py
"""

import time
import numpy as np
import pandas as pd
import tempfile
import os
from typing import Dict, List, Tuple

# Try to import Rust implementation
try:
    from ncf_rust import NCFWriter as NCFWriterRust, NCFReader as NCFReaderRust
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("[WARNING] Rust NCF module not available. Build with: cd core/ncf-rust && maturin develop --release")

# Import Python implementation
from neurolake.ncf.format.writer_optimized import NCFWriterOptimized
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType

# Import Parquet
import pyarrow.parquet as pq
import pyarrow as pa


class BenchmarkResults:
    """Store benchmark results"""

    def __init__(self, name: str):
        self.name = name
        self.write_times: List[float] = []
        self.read_times: List[float] = []
        self.file_sizes: List[int] = []

    def add_write(self, time_sec: float, file_size: int):
        self.write_times.append(time_sec)
        self.file_sizes.append(file_size)

    def add_read(self, time_sec: float):
        self.read_times.append(time_sec)

    @property
    def avg_write_time(self) -> float:
        return np.mean(self.write_times)

    @property
    def avg_read_time(self) -> float:
        return np.mean(self.read_times)

    @property
    def avg_file_size(self) -> float:
        return np.mean(self.file_sizes)

    @property
    def write_throughput(self, rows: int) -> float:
        """Rows per second"""
        return rows / self.avg_write_time

    @property
    def read_throughput(self, rows: int) -> float:
        """Rows per second"""
        return rows / self.avg_read_time


def create_benchmark_data(num_rows: int = 100000) -> pd.DataFrame:
    """Create benchmark dataset"""
    np.random.seed(42)

    return pd.DataFrame({
        'id': np.arange(num_rows, dtype=np.int64),
        'value1': np.random.randn(num_rows),
        'value2': np.random.randn(num_rows),
        'value3': np.random.randn(num_rows),
        'category': np.random.choice(['Category_A', 'Category_B', 'Category_C'], num_rows),
        'text': [f"Text_Value_{i:06d}" for i in range(num_rows)],
    })


def create_ncf_schema() -> NCFSchema:
    """Create NCF schema for benchmark"""
    return NCFSchema(
        table_name="benchmark",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="value1", data_type=NCFDataType.FLOAT64),
            ColumnSchema(name="value2", data_type=NCFDataType.FLOAT64),
            ColumnSchema(name="value3", data_type=NCFDataType.FLOAT64),
            ColumnSchema(name="category", data_type=NCFDataType.STRING),
            ColumnSchema(name="text", data_type=NCFDataType.STRING),
        ]
    )


def benchmark_python_ncf(data: pd.DataFrame, schema: NCFSchema, runs: int = 3) -> BenchmarkResults:
    """Benchmark Python NCF v1.1"""
    print("\n" + "="*80)
    print("PYTHON NCF v1.1 (Optimized)")
    print("="*80)

    results = BenchmarkResults("Python NCF v1.1")

    for run in range(runs):
        with tempfile.NamedTempFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write benchmark
            start = time.time()
            with NCFWriterOptimized(tmp_path, schema) as writer:
                writer.write(data)
            write_time = time.time() - start

            file_size = os.path.getsize(tmp_path)
            results.add_write(write_time, file_size)

            # Read benchmark
            start = time.time()
            with NCFReader(tmp_path) as reader:
                result = reader.read()
            read_time = time.time() - start

            results.add_read(read_time)

            throughput = len(data) / write_time
            print(f"  Run {run+1}: Write={write_time:.3f}s ({throughput:,.0f} rows/s), "
                  f"Read={read_time:.3f}s, Size={file_size:,} bytes")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return results


def benchmark_rust_ncf(data: pd.DataFrame, schema: NCFSchema, runs: int = 3) -> BenchmarkResults:
    """Benchmark Rust NCF v2.0"""
    if not RUST_AVAILABLE:
        print("\n[SKIPPED] Rust NCF not available")
        return None

    print("\n" + "="*80)
    print("RUST NCF v2.0 (Native)")
    print("="*80)

    results = BenchmarkResults("Rust NCF v2.0")

    for run in range(runs):
        with tempfile.NamedTempFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write benchmark
            start = time.time()
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)
            write_time = time.time() - start

            file_size = os.path.getsize(tmp_path)
            results.add_write(write_time, file_size)

            # Read benchmark
            start = time.time()
            with NCFReaderRust(tmp_path) as reader:
                result = reader.read()
            read_time = time.time() - start

            results.add_read(read_time)

            throughput = len(data) / write_time
            print(f"  Run {run+1}: Write={write_time:.3f}s ({throughput:,.0f} rows/s), "
                  f"Read={read_time:.3f}s, Size={file_size:,} bytes")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return results


def benchmark_parquet(data: pd.DataFrame, runs: int = 3) -> BenchmarkResults:
    """Benchmark Apache Parquet"""
    print("\n" + "="*80)
    print("APACHE PARQUET (Baseline)")
    print("="*80)

    results = BenchmarkResults("Parquet")

    for run in range(runs):
        with tempfile.NamedTempFile(suffix='.parquet', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write benchmark
            start = time.time()
            data.to_parquet(tmp_path, engine='pyarrow', compression='snappy')
            write_time = time.time() - start

            file_size = os.path.getsize(tmp_path)
            results.add_write(write_time, file_size)

            # Read benchmark
            start = time.time()
            result = pd.read_parquet(tmp_path)
            read_time = time.time() - start

            results.add_read(read_time)

            throughput = len(data) / write_time
            print(f"  Run {run+1}: Write={write_time:.3f}s ({throughput:,.0f} rows/s), "
                  f"Read={read_time:.3f}s, Size={file_size:,} bytes")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return results


def print_summary(results: List[BenchmarkResults], data_rows: int):
    """Print comprehensive summary"""
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    # Filter out None results
    results = [r for r in results if r is not None]

    # Write performance
    print("\nWrite Performance:")
    print(f"  {'Implementation':<20} {'Avg Time':<12} {'Throughput':<20} {'vs Baseline':<15}")
    print("  " + "-"*76)

    baseline_write_throughput = None
    for r in results:
        throughput = data_rows / r.avg_write_time
        vs_baseline = ""

        if r.name == "Parquet":
            baseline_write_throughput = throughput
        elif baseline_write_throughput:
            ratio = throughput / baseline_write_throughput
            vs_baseline = f"{ratio:.2f}x"
            if ratio >= 1.0:
                vs_baseline += " [FASTER]"
            else:
                vs_baseline += " slower"

        print(f"  {r.name:<20} {r.avg_write_time:>7.3f}s     "
              f"{throughput:>12,.0f} rows/s   {vs_baseline:<15}")

    # Read performance
    print("\nRead Performance:")
    print(f"  {'Implementation':<20} {'Avg Time':<12} {'Throughput':<20} {'vs Baseline':<15}")
    print("  " + "-"*76)

    baseline_read_throughput = None
    for r in results:
        throughput = data_rows / r.avg_read_time
        vs_baseline = ""

        if r.name == "Parquet":
            baseline_read_throughput = throughput
        elif baseline_read_throughput:
            ratio = throughput / baseline_read_throughput
            vs_baseline = f"{ratio:.2f}x"
            if ratio >= 1.0:
                vs_baseline += " [FASTER]"
            else:
                vs_baseline += " slower"

        print(f"  {r.name:<20} {r.avg_read_time:>7.3f}s     "
              f"{throughput:>12,.0f} rows/s   {vs_baseline:<15}")

    # File size
    print("\nFile Size:")
    print(f"  {'Implementation':<20} {'Avg Size':<15} {'Compression':<15} {'vs Baseline':<15}")
    print("  " + "-"*76)

    # Calculate original data size (rough estimate)
    original_size = data_rows * (8 + 8 + 8 + 8 + 15 + 20)  # Rough estimate

    baseline_size = None
    for r in results:
        compression_ratio = original_size / r.avg_file_size
        vs_baseline = ""

        if r.name == "Parquet":
            baseline_size = r.avg_file_size
        elif baseline_size:
            ratio = baseline_size / r.avg_file_size
            vs_baseline = f"{ratio:.2f}x smaller" if ratio > 1.0 else f"{1/ratio:.2f}x larger"

        print(f"  {r.name:<20} {r.avg_file_size:>10,.0f} B    "
              f"{compression_ratio:>6.1f}x          {vs_baseline:<15}")

    # Overall verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)

    for r in results:
        if r.name == "Parquet":
            continue

        parquet_result = next((pr for pr in results if pr.name == "Parquet"), None)
        if not parquet_result:
            continue

        write_ratio = (data_rows / r.avg_write_time) / (data_rows / parquet_result.avg_write_time)
        size_ratio = parquet_result.avg_file_size / r.avg_file_size

        print(f"\n{r.name}:")
        print(f"  Write Speed: {write_ratio:.2f}x vs Parquet")
        print(f"  File Size: {size_ratio:.2f}x better compression")

        if write_ratio >= 1.0 and size_ratio > 1.0:
            print(f"  STATUS: [SUCCESS] Faster AND better compression!")
        elif write_ratio >= 0.8:
            print(f"  STATUS: [GOOD] Competitive performance")
        else:
            print(f"  STATUS: [NEEDS OPTIMIZATION]")


def main():
    """Run comprehensive benchmark"""
    print("="*80)
    print("NCF RUST vs PYTHON BENCHMARK")
    print("="*80)

    # Configuration
    NUM_ROWS = 100000
    NUM_RUNS = 3

    print(f"\nConfiguration:")
    print(f"  Rows: {NUM_ROWS:,}")
    print(f"  Runs: {NUM_RUNS}")
    print(f"  Rust Available: {RUST_AVAILABLE}")

    # Create data
    print(f"\nCreating benchmark dataset...")
    data = create_benchmark_data(NUM_ROWS)
    schema = create_ncf_schema()
    print(f"  Dataset size: {len(data):,} rows, {len(data.columns)} columns")

    # Run benchmarks
    results = []

    # Python NCF
    results.append(benchmark_python_ncf(data, schema, NUM_RUNS))

    # Rust NCF
    if RUST_AVAILABLE:
        results.append(benchmark_rust_ncf(data, schema, NUM_RUNS))

    # Parquet
    results.append(benchmark_parquet(data, NUM_RUNS))

    # Summary
    print_summary(results, NUM_ROWS)

    print("\n" + "="*80)
    print("BENCHMARK COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
