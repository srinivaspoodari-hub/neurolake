"""
Performance Benchmark: NCFFastReader (Parallel Reader)
Compare NCFFastReader vs NCFReader vs Parquet
"""

import time
import os
from tempfile import NamedTemporaryFile

print("="*80)
print("NCF FAST READER - PERFORMANCE BENCHMARK")
print("="*80)

# Import implementations
try:
    from ncf_rust import NCFWriter, NCFReader, NCFFastReader
    from ncf_rust import NCFSchema, ColumnSchema, NCFDataType
    RUST_AVAILABLE = True
    print("\n[OK] Rust NCF imported (NCFReader + NCFFastReader)")
except ImportError as e:
    print(f"\n[FAIL] Could not import Rust NCF: {e}")
    RUST_AVAILABLE = False

try:
    import pyarrow.parquet as pq
    import pyarrow as pa
    PARQUET_AVAILABLE = True
    print("[OK] Apache Parquet imported")
except ImportError:
    print("[SKIP] Apache Parquet not available")
    PARQUET_AVAILABLE = False

if not RUST_AVAILABLE:
    print("\n[ERROR] Rust NCF required for benchmarking")
    exit(1)

print("\n" + "="*80)
print("BENCHMARK CONFIGURATION")
print("="*80)

# Test configurations
SIZES = [1_000, 10_000, 100_000]
ITERATIONS = 3

print(f"\nDataset sizes: {SIZES}")
print(f"Iterations per size: {ITERATIONS}")
print(f"Data types: int64, float64, string (3 columns)")

# Create test data generator
def generate_data(num_rows):
    """Generate test data"""
    return {
        'id': list(range(num_rows)),
        'value': [float(i) * 1.5 for i in range(num_rows)],
        'name': [f'user_{i:06d}' for i in range(num_rows)]
    }

# Benchmark results storage
results = {
    'fast': {'read': []},
    'regular': {'read': []},
    'parquet': {'read': []}
}

print("\n" + "="*80)
print("RUNNING BENCHMARKS")
print("="*80)

for size in SIZES:
    print(f"\n{'='*80}")
    print(f"Dataset Size: {size:,} rows")
    print(f"{'='*80}")

    # Generate test data once
    data = generate_data(size)

    # Create test file
    with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write once
        schema = NCFSchema("benchmark", [
            ColumnSchema("id", NCFDataType.int64(), None, True),
            ColumnSchema("value", NCFDataType.float64(), None, True),
            ColumnSchema("name", NCFDataType.string(), None, True),
        ], 0, 1)

        writer = NCFWriter(tmp_path, schema)
        writer.write(data)
        writer.close()

        file_size = os.path.getsize(tmp_path)
        print(f"\nFile size: {file_size:,} bytes")

        # === NCFFastReader (Parallel) ===
        print(f"\n[NCF Fast Reader] Benchmarking {size:,} rows...")

        read_times = []
        for iteration in range(ITERATIONS):
            reader = NCFFastReader(tmp_path)
            start = time.time()
            result = reader.read()
            read_time = time.time() - start
            read_times.append(read_time)

            # Verify correctness
            assert len(result['id']) == size, f"Row count mismatch"

        avg_read = sum(read_times) / len(read_times)
        results['fast']['read'].append(avg_read)

        read_throughput = size / avg_read
        print(f"  Read:  {avg_read:.3f}s ({read_throughput:,.0f} rows/sec)")

        # === NCFReader (Regular) ===
        print(f"\n[NCF Regular Reader] Benchmarking {size:,} rows...")

        read_times = []
        for iteration in range(ITERATIONS):
            reader = NCFReader(tmp_path)
            start = time.time()
            result = reader.read()
            read_time = time.time() - start
            read_times.append(read_time)

        avg_read = sum(read_times) / len(read_times)
        results['regular']['read'].append(avg_read)

        read_throughput = size / avg_read
        print(f"  Read:  {avg_read:.3f}s ({read_throughput:,.0f} rows/sec)")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # === APACHE PARQUET ===
    if PARQUET_AVAILABLE:
        with NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            table = pa.table(data)
            pq.write_table(table, tmp_path, compression='snappy')

            print(f"\n[Apache Parquet] Benchmarking {size:,} rows...")

            read_times = []
            for iteration in range(ITERATIONS):
                start = time.time()
                result_table = pq.read_table(tmp_path)
                read_time = time.time() - start
                read_times.append(read_time)

            avg_read = sum(read_times) / len(read_times)
            results['parquet']['read'].append(avg_read)

            read_throughput = size / avg_read
            print(f"  Read:  {avg_read:.3f}s ({read_throughput:,.0f} rows/sec)")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# === RESULTS SUMMARY ===
print("\n" + "="*80)
print("BENCHMARK RESULTS SUMMARY")
print("="*80)

for i, size in enumerate(SIZES):
    print(f"\n{'='*80}")
    print(f"Dataset: {size:,} rows")
    print(f"{'='*80}")

    print(f"\n{'Implementation':<25} {'Read (rows/s)':<20} {'Speedup vs Regular':<20}")
    print("-" * 80)

    # Fast
    if results['fast']['read']:
        fast_speed = size / results['fast']['read'][i]
        print(f"{'NCF Fast (Parallel)':<25} {fast_speed:>18,.0f}  {'baseline':>18}")

    # Regular
    if results['regular']['read']:
        regular_speed = size / results['regular']['read'][i]
        speedup = results['regular']['read'][i] / results['fast']['read'][i]
        print(f"{'NCF Regular':<25} {regular_speed:>18,.0f}  {speedup:>17.2f}x")

    # Parquet
    if results['parquet']['read']:
        parquet_speed = size / results['parquet']['read'][i]
        speedup_vs_regular = results['parquet']['read'][i] / results['regular']['read'][i]
        speedup_vs_fast = results['parquet']['read'][i] / results['fast']['read'][i]
        print(f"{'Parquet (Snappy)':<25} {parquet_speed:>18,.0f}  {speedup_vs_regular:>17.2f}x")

    # Speedup calculations
    if results['fast']['read'] and results['regular']['read']:
        print(f"\n{'Performance Improvement:':<40}")
        speedup = results['regular']['read'][i] / results['fast']['read'][i]
        print(f"  Fast Reader: {speedup:.2f}x faster than Regular")

    if results['fast']['read'] and results['parquet']['read']:
        fast_vs_parquet = results['parquet']['read'][i] / results['fast']['read'][i]
        if fast_vs_parquet > 1:
            print(f"  Fast Reader: {fast_vs_parquet:.2f}x faster than Parquet")
        else:
            print(f"  Fast Reader: {1/fast_vs_parquet:.2f}x slower than Parquet")

print("\n" + "="*80)
print("BENCHMARK COMPLETE")
print("="*80)
print("\nKey Findings:")
print("- NCF Fast Reader uses parallel decompression + deserialization")
print("- Expected 2-3x speedup over regular NCF reader")
print("- Speedups improve with larger datasets")
print("="*80)
