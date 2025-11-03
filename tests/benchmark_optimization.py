"""
Benchmark NCF optimization improvements

Compares:
1. Original NCF writer
2. Optimized NCF writer (Phase 1)
3. Parquet (baseline)
"""

import numpy as np
import pandas as pd
import tempfile
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.writer_optimized import NCFWriterOptimized
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType, SemanticType


def create_benchmark_dataset(num_rows=100_000):
    """Create benchmark dataset"""
    print(f"\nCreating benchmark dataset ({num_rows:,} rows)...")
    data = pd.DataFrame({
        "id": range(num_rows),
        "value": np.random.rand(num_rows),
        "category": np.random.choice(["A", "B", "C", "D", "E"], num_rows),
        "score": np.random.randint(0, 100, num_rows),
        "name": [f"User_{i}" for i in range(num_rows)],
        "email": [f"user{i}@example.com" for i in range(num_rows)],
    })

    print(f"  Dataset size: {data.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    return data


def create_schema():
    """Create NCF schema"""
    return NCFSchema(
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


def benchmark_ncf_original(data, runs=3):
    """Benchmark original NCF writer"""
    print("\n" + "=" * 80)
    print("ORIGINAL NCF WRITER")
    print("=" * 80)

    schema = create_schema()
    times = []
    sizes = []

    for i in range(runs):
        with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            start = time.time()
            with NCFWriter(tmp_path, schema, compression="zstd") as writer:
                writer.write(data)
            write_time = time.time() - start

            size = os.path.getsize(tmp_path)

            times.append(write_time)
            sizes.append(size)

            print(f"  Run {i+1}: {write_time:.3f}s ({len(data)/write_time:,.0f} rows/sec), Size: {size:,} bytes")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    avg_time = sum(times) / len(times)
    avg_size = sum(sizes) / len(sizes)

    print(f"\n  Average: {avg_time:.3f}s ({len(data)/avg_time:,.0f} rows/sec)")
    print(f"  File size: {avg_size:,} bytes ({avg_size/1024/1024:.2f} MB)")

    return {"write_time": avg_time, "write_speed": len(data)/avg_time, "file_size": avg_size}


def benchmark_ncf_optimized(data, runs=3):
    """Benchmark optimized NCF writer"""
    print("\n" + "=" * 80)
    print("OPTIMIZED NCF WRITER (Phase 1)")
    print("=" * 80)

    schema = create_schema()
    times = []
    sizes = []

    for i in range(runs):
        with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            start = time.time()
            with NCFWriterOptimized(tmp_path, schema, compression="zstd", compression_level=1) as writer:
                writer.write(data)
            write_time = time.time() - start

            size = os.path.getsize(tmp_path)

            times.append(write_time)
            sizes.append(size)

            print(f"  Run {i+1}: {write_time:.3f}s ({len(data)/write_time:,.0f} rows/sec), Size: {size:,} bytes")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    avg_time = sum(times) / len(times)
    avg_size = sum(sizes) / len(sizes)

    print(f"\n  Average: {avg_time:.3f}s ({len(data)/avg_time:,.0f} rows/sec)")
    print(f"  File size: {avg_size:,} bytes ({avg_size/1024/1024:.2f} MB)")

    return {"write_time": avg_time, "write_speed": len(data)/avg_time, "file_size": avg_size}


def benchmark_parquet(data, runs=3):
    """Benchmark Parquet writer"""
    print("\n" + "=" * 80)
    print("PARQUET (BASELINE)")
    print("=" * 80)

    times = []
    sizes = []

    for i in range(runs):
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            start = time.time()
            data.to_parquet(tmp_path, compression="snappy", engine="pyarrow")
            write_time = time.time() - start

            size = os.path.getsize(tmp_path)

            times.append(write_time)
            sizes.append(size)

            print(f"  Run {i+1}: {write_time:.3f}s ({len(data)/write_time:,.0f} rows/sec), Size: {size:,} bytes")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    avg_time = sum(times) / len(times)
    avg_size = sum(sizes) / len(sizes)

    print(f"\n  Average: {avg_time:.3f}s ({len(data)/avg_time:,.0f} rows/sec)")
    print(f"  File size: {avg_size:,} bytes ({avg_size/1024/1024:.2f} MB)")

    return {"write_time": avg_time, "write_speed": len(data)/avg_time, "file_size": avg_size}


def print_comparison(original, optimized, parquet):
    """Print comparison table"""
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    print(f"\n{'Metric':<25} {'Original NCF':<20} {'Optimized NCF':<20} {'Parquet':<20}")
    print("-" * 85)

    # Write speed
    print(f"{'Write Speed':<25} {original['write_speed']:>15,.0f} r/s {optimized['write_speed']:>15,.0f} r/s {parquet['write_speed']:>15,.0f} r/s")

    # Write time
    print(f"{'Write Time':<25} {original['write_time']:>18.3f}s {optimized['write_time']:>18.3f}s {parquet['write_time']:>18.3f}s")

    # File size
    print(f"{'File Size':<25} {original['file_size']:>15,} B {optimized['file_size']:>15,} B {parquet['file_size']:>15,} B")
    print(f"{'File Size (MB)':<25} {original['file_size']/1024/1024:>18.2f} {optimized['file_size']/1024/1024:>18.2f} {parquet['file_size']/1024/1024:>18.2f}")

    print("\n" + "=" * 80)
    print("IMPROVEMENTS")
    print("=" * 80)

    # Speedup vs original
    speedup = optimized['write_speed'] / original['write_speed']
    print(f"\nOptimized vs Original NCF:")
    print(f"  Speed improvement: {speedup:.2f}x faster")
    print(f"  Time reduction: {(1 - optimized['write_time']/original['write_time'])*100:.1f}% faster")

    size_change = (optimized['file_size'] - original['file_size']) / original['file_size'] * 100
    print(f"  File size change: {size_change:+.1f}%")

    # Gap to Parquet
    gap_original = parquet['write_speed'] / original['write_speed']
    gap_optimized = parquet['write_speed'] / optimized['write_speed']

    print(f"\nGap to Parquet:")
    print(f"  Original: Parquet is {gap_original:.2f}x faster")
    print(f"  Optimized: Parquet is {gap_optimized:.2f}x faster")
    print(f"  Gap closed: {(gap_original - gap_optimized) / gap_original * 100:.1f}%")

    # Compression advantage
    comp_original = parquet['file_size'] / original['file_size']
    comp_optimized = parquet['file_size'] / optimized['file_size']

    print(f"\nCompression Advantage:")
    print(f"  Original NCF: {comp_original:.2f}x smaller than Parquet")
    print(f"  Optimized NCF: {comp_optimized:.2f}x smaller than Parquet")

    print("\n" + "=" * 80)
    print("TARGET ASSESSMENT")
    print("=" * 80)

    target_speed = 600_000  # 600K rows/sec target
    target_met = "YES [OK]" if optimized['write_speed'] >= target_speed else "NO [X]"

    print(f"\nPhase 1 Target: 600-700K rows/sec")
    print(f"Achieved: {optimized['write_speed']:,.0f} rows/sec")
    print(f"Target met: {target_met}")

    if optimized['write_speed'] < target_speed:
        shortfall = (target_speed - optimized['write_speed']) / target_speed * 100
        print(f"Shortfall: {shortfall:.1f}% below target")
        print(f"\nRecommendation: Proceed to Phase 2 (Cython acceleration)")
    else:
        print(f"\nRecommendation: Phase 1 optimizations successful! Consider Phase 2 for further gains.")


def main():
    """Main benchmark function"""
    print("\n" + "=" * 80)
    print("NCF OPTIMIZATION BENCHMARK")
    print("=" * 80)
    print("\nComparing:")
    print("  1. Original NCF writer (writer.py)")
    print("  2. Optimized NCF writer (writer_optimized.py) - Phase 1")
    print("  3. Parquet baseline")
    print("\nOptimizations applied:")
    print("  [OK] Fast string serialization (pre-allocated buffer)")
    print("  [OK] Single-pass statistics generation")
    print("  [OK] Lower compression level (1 vs 3)")
    print("  [OK] Cached schema lookups")

    # Create test data
    data = create_benchmark_dataset(100_000)

    # Run benchmarks
    original_results = benchmark_ncf_original(data, runs=3)
    optimized_results = benchmark_ncf_optimized(data, runs=3)
    parquet_results = benchmark_parquet(data, runs=3)

    # Print comparison
    print_comparison(original_results, optimized_results, parquet_results)


if __name__ == "__main__":
    main()
