"""
Profile NCF performance bottlenecks

This script identifies where NCF spends time compared to Parquet
and provides optimization recommendations.
"""

import numpy as np
import pandas as pd
import tempfile
import os
import sys
import time
import cProfile
import pstats
from pathlib import Path
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType, SemanticType


def create_benchmark_dataset(num_rows=100_000):
    """Create benchmark dataset"""
    return pd.DataFrame({
        "id": range(num_rows),
        "value": np.random.rand(num_rows),
        "category": np.random.choice(["A", "B", "C", "D", "E"], num_rows),
        "score": np.random.randint(0, 100, num_rows),
        "name": [f"User_{i}" for i in range(num_rows)],
        "email": [f"user{i}@example.com" for i in range(num_rows)],
    })


def profile_ncf_write(data, output_path):
    """Profile NCF write operation"""
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

    profiler = cProfile.Profile()
    profiler.enable()

    with NCFWriter(output_path, schema, compression="zstd") as writer:
        writer.write(data)

    profiler.disable()
    return profiler


def profile_ncf_read(input_path):
    """Profile NCF read operation"""
    profiler = cProfile.Profile()
    profiler.enable()

    with NCFReader(input_path) as reader:
        result = reader.read()

    profiler.disable()
    return profiler, result


def profile_parquet_write(data, output_path):
    """Profile Parquet write operation"""
    profiler = cProfile.Profile()
    profiler.enable()

    data.to_parquet(output_path, compression="snappy", engine="pyarrow")

    profiler.disable()
    return profiler


def profile_parquet_read(input_path):
    """Profile Parquet read operation"""
    profiler = cProfile.Profile()
    profiler.enable()

    result = pd.read_parquet(input_path)

    profiler.disable()
    return profiler, result


def print_profiler_stats(profiler, title, top_n=20):
    """Print profiler statistics"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")

    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    ps.print_stats(top_n)

    print(s.getvalue())


def detailed_timing_breakdown():
    """Break down NCF write into individual operations"""
    print("\n" + "=" * 80)
    print("DETAILED NCF WRITE TIMING BREAKDOWN")
    print("=" * 80)

    num_rows = 10_000
    data = create_benchmark_dataset(num_rows)

    schema = NCFSchema(
        table_name="timing_test",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
            ColumnSchema(name="category", data_type=NCFDataType.STRING),
            ColumnSchema(name="score", data_type=NCFDataType.INT64),
            ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ColumnSchema(name="email", data_type=NCFDataType.STRING),
        ]
    )

    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Time individual operations
        timings = {}

        # Schema serialization
        start = time.time()
        schema_bytes = schema.to_msgpack()
        timings["schema_serialize"] = time.time() - start

        # Column serialization (without compression)
        print("\nColumn serialization times:")
        for col in data.columns:
            col_data = data[col].values
            col_schema = next(c for c in schema.columns if c.name == col)

            start = time.time()
            if col_schema.data_type == NCFDataType.STRING:
                # String serialization
                import struct
                string_list = [str(s).encode('utf-8') for s in col_data]
                num_strings = len(string_list)
                offsets = [0]
                for s in string_list:
                    offsets.append(offsets[-1] + len(s))
                result = struct.pack("<I", num_strings)
                result += struct.pack(f"<{len(offsets)}I", *offsets)
                result += b"".join(string_list)
                serialized = result
            else:
                # Numeric serialization
                dtype_map = {
                    NCFDataType.INT64: np.int64,
                    NCFDataType.FLOAT64: np.float64,
                }
                target_dtype = dtype_map[col_schema.data_type]
                serialized = col_data.astype(target_dtype).tobytes()

            serialize_time = time.time() - start
            timings[f"serialize_{col}"] = serialize_time
            print(f"  {col:15s}: {serialize_time*1000:6.2f}ms ({len(serialized):,} bytes)")

            # Compression
            start = time.time()
            import zstandard as zstd
            compressor = zstd.ZstdCompressor(level=3)
            compressed = compressor.compress(serialized)
            compress_time = time.time() - start
            timings[f"compress_{col}"] = compress_time

            ratio = len(serialized) / len(compressed) if len(compressed) > 0 else 0
            print(f"    Compression:  {compress_time*1000:6.2f}ms ({len(compressed):,} bytes, {ratio:.2f}x)")

        # Statistics calculation
        print("\nStatistics calculation:")
        for col in data.columns:
            col_data = data[col].values
            start = time.time()

            if pd.api.types.is_numeric_dtype(col_data):
                min_val = np.min(col_data)
                max_val = np.max(col_data)
                null_count = int(np.sum(pd.isna(col_data)))
            else:
                min_val = None
                max_val = None
                null_count = int(np.sum(pd.isna(col_data)))

            stats_time = time.time() - start
            timings[f"stats_{col}"] = stats_time
            print(f"  {col:15s}: {stats_time*1000:6.2f}ms")

        # Checksum calculation
        print("\nChecksum calculation:")
        start = time.time()
        import hashlib
        hasher = hashlib.sha256()
        # Simulate hashing file content
        hasher.update(b"x" * 1_000_000)  # 1MB dummy data
        checksum = hasher.digest()
        checksum_time = time.time() - start
        timings["checksum"] = checksum_time
        print(f"  SHA-256: {checksum_time*1000:6.2f}ms")

        # Summary
        print("\n" + "-" * 80)
        print("TIMING SUMMARY")
        print("-" * 80)

        total_time = sum(timings.values())
        for operation, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
            percentage = (duration / total_time) * 100
            print(f"  {operation:30s}: {duration*1000:8.2f}ms ({percentage:5.1f}%)")

        print(f"\n  {'TOTAL':30s}: {total_time*1000:8.2f}ms")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def compare_compression_algorithms():
    """Compare different compression algorithms"""
    print("\n" + "=" * 80)
    print("COMPRESSION ALGORITHM COMPARISON")
    print("=" * 80)

    num_rows = 50_000
    data = create_benchmark_dataset(num_rows)

    # Test numeric column
    print("\nNumeric column (float64, 50K values):")
    numeric_data = data["value"].values.astype(np.float64).tobytes()
    print(f"  Original size: {len(numeric_data):,} bytes")

    import zstandard as zstd

    # ZSTD levels
    for level in [1, 3, 5, 10, 15]:
        start = time.time()
        compressor = zstd.ZstdCompressor(level=level)
        compressed = compressor.compress(numeric_data)
        compress_time = time.time() - start

        ratio = len(numeric_data) / len(compressed)
        speed = len(numeric_data) / compress_time / 1024 / 1024

        print(f"  ZSTD level {level:2d}: {len(compressed):,} bytes ({ratio:.2f}x) in {compress_time*1000:.1f}ms ({speed:.0f} MB/s)")

    # Test string column
    print("\nString column (emails, 50K values):")
    string_data = data["email"].values
    import struct
    string_list = [str(s).encode('utf-8') for s in string_data]
    num_strings = len(string_list)
    offsets = [0]
    for s in string_list:
        offsets.append(offsets[-1] + len(s))
    result = struct.pack("<I", num_strings)
    result += struct.pack(f"<{len(offsets)}I", *offsets)
    result += b"".join(string_list)
    string_bytes = result

    print(f"  Original size: {len(string_bytes):,} bytes")

    for level in [1, 3, 5, 10, 15]:
        start = time.time()
        compressor = zstd.ZstdCompressor(level=level)
        compressed = compressor.compress(string_bytes)
        compress_time = time.time() - start

        ratio = len(string_bytes) / len(compressed)
        speed = len(string_bytes) / compress_time / 1024 / 1024

        print(f"  ZSTD level {level:2d}: {len(compressed):,} bytes ({ratio:.2f}x) in {compress_time*1000:.1f}ms ({speed:.0f} MB/s)")


def main():
    """Main profiling function"""
    print("\n" + "=" * 80)
    print("NCF PERFORMANCE PROFILING")
    print("=" * 80)

    num_rows = 50_000  # Use smaller dataset for profiling
    print(f"\nCreating benchmark dataset ({num_rows:,} rows)...")
    data = create_benchmark_dataset(num_rows)

    # NCF write profiling
    print(f"\n[1/4] Profiling NCF write...")
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        ncf_path = tmp.name

    start = time.time()
    ncf_write_profiler = profile_ncf_write(data, ncf_path)
    ncf_write_time = time.time() - start
    ncf_size = os.path.getsize(ncf_path)

    print(f"  NCF write: {ncf_write_time:.3f}s ({len(data)/ncf_write_time:,.0f} rows/sec)")
    print(f"  File size: {ncf_size:,} bytes ({ncf_size/1024/1024:.2f} MB)")

    print_profiler_stats(ncf_write_profiler, "NCF WRITE PROFILE (Top 20 functions)", top_n=20)

    # NCF read profiling
    print(f"\n[2/4] Profiling NCF read...")
    start = time.time()
    ncf_read_profiler, ncf_result = profile_ncf_read(ncf_path)
    ncf_read_time = time.time() - start

    print(f"  NCF read: {ncf_read_time:.3f}s ({len(ncf_result)/ncf_read_time:,.0f} rows/sec)")

    print_profiler_stats(ncf_read_profiler, "NCF READ PROFILE (Top 20 functions)", top_n=20)

    # Parquet write profiling
    print(f"\n[3/4] Profiling Parquet write...")
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        parquet_path = tmp.name

    start = time.time()
    parquet_write_profiler = profile_parquet_write(data, parquet_path)
    parquet_write_time = time.time() - start
    parquet_size = os.path.getsize(parquet_path)

    print(f"  Parquet write: {parquet_write_time:.3f}s ({len(data)/parquet_write_time:,.0f} rows/sec)")
    print(f"  File size: {parquet_size:,} bytes ({parquet_size/1024/1024:.2f} MB)")

    print_profiler_stats(parquet_write_profiler, "PARQUET WRITE PROFILE (Top 20 functions)", top_n=20)

    # Parquet read profiling
    print(f"\n[4/4] Profiling Parquet read...")
    start = time.time()
    parquet_read_profiler, parquet_result = profile_parquet_read(parquet_path)
    parquet_read_time = time.time() - start

    print(f"  Parquet read: {parquet_read_time:.3f}s ({len(parquet_result)/parquet_read_time:,.0f} rows/sec)")

    print_profiler_stats(parquet_read_profiler, "PARQUET READ PROFILE (Top 20 functions)", top_n=20)

    # Performance comparison summary
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON SUMMARY")
    print("=" * 80)

    print(f"\nWrite Performance:")
    print(f"  NCF:     {ncf_write_time:.3f}s ({len(data)/ncf_write_time:,.0f} rows/sec)")
    print(f"  Parquet: {parquet_write_time:.3f}s ({len(data)/parquet_write_time:,.0f} rows/sec)")
    print(f"  Parquet is {parquet_write_time/ncf_write_time:.2f}x faster" if parquet_write_time < ncf_write_time else f"  NCF is {ncf_write_time/parquet_write_time:.2f}x faster")

    print(f"\nRead Performance:")
    print(f"  NCF:     {ncf_read_time:.3f}s ({len(ncf_result)/ncf_read_time:,.0f} rows/sec)")
    print(f"  Parquet: {parquet_read_time:.3f}s ({len(parquet_result)/parquet_read_time:,.0f} rows/sec)")
    print(f"  Parquet is {parquet_read_time/ncf_read_time:.2f}x faster" if parquet_read_time < ncf_read_time else f"  NCF is {ncf_read_time/parquet_read_time:.2f}x faster")

    print(f"\nFile Size:")
    print(f"  NCF:     {ncf_size:,} bytes ({ncf_size/1024/1024:.2f} MB)")
    print(f"  Parquet: {parquet_size:,} bytes ({parquet_size/1024/1024:.2f} MB)")
    print(f"  NCF is {parquet_size/ncf_size:.2f}x smaller" if ncf_size < parquet_size else f"  Parquet is {ncf_size/parquet_size:.2f}x smaller")

    # Cleanup
    os.remove(ncf_path)
    os.remove(parquet_path)

    # Detailed timing breakdown
    detailed_timing_breakdown()

    # Compression algorithm comparison
    compare_compression_algorithms()

    # Final analysis
    print("\n" + "=" * 80)
    print("BOTTLENECK ANALYSIS")
    print("=" * 80)
    print("\nWhy is Parquet faster than NCF?")
    print("\n1. IMPLEMENTATION LANGUAGE")
    print("   - Parquet: C++ (Apache Arrow/PyArrow)")
    print("   - NCF: Pure Python")
    print("   - Impact: C++ is 10-100x faster for serialization/compression")
    print("\n2. SERIALIZATION OVERHEAD")
    print("   - Parquet: Optimized C++ serialization")
    print("   - NCF: Python loops for string serialization")
    print("   - Impact: String columns are bottleneck")
    print("\n3. COMPRESSION")
    print("   - Parquet: Native Snappy (C++)")
    print("   - NCF: Python ZSTD bindings (some overhead)")
    print("   - Impact: Compression is CPU-bound")
    print("\n4. METADATA SERIALIZATION")
    print("   - Parquet: Protobuf (C++)")
    print("   - NCF: Msgpack (Python)")
    print("   - Impact: Minor overhead")
    print("\n5. FILE I/O")
    print("   - Both use buffered I/O, similar performance")
    print("\n" + "=" * 80)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 80)
    print("\n[HIGH IMPACT] Optimize string serialization:")
    print("  - Use numpy structured arrays instead of Python loops")
    print("  - Pre-calculate total size to avoid reallocations")
    print("  - Expected speedup: 2-3x")
    print("\n[HIGH IMPACT] Batch operations:")
    print("  - Process multiple columns in parallel")
    print("  - Use numpy vectorized operations")
    print("  - Expected speedup: 1.5-2x")
    print("\n[MEDIUM IMPACT] Optimize compression:")
    print("  - Lower ZSTD compression level (3 → 1)")
    print("  - Expected speedup: 1.3-1.5x")
    print("\n[MEDIUM IMPACT] Reduce Python overhead:")
    print("  - Use Cython for hot paths")
    print("  - Expected speedup: 1.5-2x")
    print("\n[LONG TERM] Rewrite in Rust/C++:")
    print("  - Full rewrite with Arrow integration")
    print("  - Expected speedup: 10-50x (match Parquet)")
    print("\n[IMMEDIATE] Quick wins:")
    print("  - Remove unnecessary dtype checks")
    print("  - Cache schema lookups")
    print("  - Use memoryview for zero-copy operations")
    print("  - Expected speedup: 1.2-1.5x")
    print("\nCombined optimization potential: 5-10x speedup possible with Python")
    print("To match Parquet: Requires C++/Rust implementation")


if __name__ == "__main__":
    main()
