"""
Optimized benchmark showing parallel reader benefits with more columns
"""
import time
from tempfile import NamedTemporaryFile
import os

from ncf_rust import NCFWriter, NCFReader, NCFFastReader
from ncf_rust import NCFSchema, ColumnSchema, NCFDataType

try:
    import pyarrow.parquet as pq
    import pyarrow as pa
    PARQUET = True
except:
    PARQUET = False

print("NCF Fast Reader - Optimized Benchmark (More Columns)")
print("=" * 70)

# Test with many columns to show parallel benefits
num_rows = 100_000
num_numeric_cols = 8  # More columns = more parallelism benefit

print(f"\nDataset: {num_rows:,} rows x {num_numeric_cols + 2} columns")
print(f"Columns: {num_numeric_cols} numeric + 2 string columns")

# Generate data with many columns
data = {
    'id': list(range(num_rows)),
}

# Add many numeric columns
for i in range(num_numeric_cols):
    data[f'value_{i}'] = [float(j) * (i + 1.5) for j in range(num_rows)]

# Add string columns
data['name'] = [f'user_{i:06d}' for i in range(num_rows)]
data['email'] = [f'user{i}@example.com' for i in range(num_rows)]

# Create schema
columns = [ColumnSchema("id", NCFDataType.int64(), None, True)]
for i in range(num_numeric_cols):
    columns.append(ColumnSchema(f"value_{i}", NCFDataType.float64(), None, True))
columns.append(ColumnSchema("name", NCFDataType.string(), None, True))
columns.append(ColumnSchema("email", NCFDataType.string(), None, True))

schema = NCFSchema("test", columns, 0, 1)

# Write NCF file
with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
    ncf_path = tmp.name

try:
    # Write NCF
    print("\nWriting NCF file...")
    writer = NCFWriter(ncf_path, schema)
    write_start = time.time()
    writer.write(data)
    writer.close()
    write_time = time.time() - write_start
    ncf_size = os.path.getsize(ncf_path)

    print(f"  NCF file size: {ncf_size:,} bytes ({ncf_size/1024/1024:.2f} MB)")
    print(f"  Write speed: {num_rows/write_time:,.0f} rows/sec")

    # Benchmark Regular Reader
    print("\n[Regular NCF Reader]")
    times = []
    for i in range(3):
        reader = NCFReader(ncf_path)
        start = time.time()
        result = reader.read()
        elapsed = time.time() - start
        times.append(elapsed)
        if i == 0:
            print(f"  Warmup: {elapsed:.4f}s ({num_rows/elapsed:,.0f} rows/sec)")

    avg_time = sum(times[1:]) / 2  # Average of last 2 runs
    regular_speed = num_rows / avg_time
    print(f"  Average: {avg_time:.4f}s ({regular_speed:,.0f} rows/sec)")

    # Benchmark Fast Reader
    print("\n[Fast NCF Reader (Parallel)]")
    times = []
    for i in range(3):
        reader = NCFFastReader(ncf_path)
        start = time.time()
        result = reader.read()
        elapsed = time.time() - start
        times.append(elapsed)
        if i == 0:
            print(f"  Warmup: {elapsed:.4f}s ({num_rows/elapsed:,.0f} rows/sec)")

    avg_time = sum(times[1:]) / 2  # Average of last 2 runs
    fast_speed = num_rows / avg_time
    print(f"  Average: {avg_time:.4f}s ({fast_speed:,.0f} rows/sec)")

    # Calculate speedup
    speedup = fast_speed / regular_speed
    print(f"\n  Speedup: {speedup:.2f}x faster than Regular")

    # Parquet comparison
    if PARQUET:
        with NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            parquet_path = tmp.name

        try:
            # Write Parquet
            print("\n[Apache Parquet (Snappy)]")
            table = pa.table(data)
            pq.write_table(table, parquet_path, compression='snappy')
            parquet_size = os.path.getsize(parquet_path)
            print(f"  File size: {parquet_size:,} bytes ({parquet_size/1024/1024:.2f} MB)")

            # Benchmark Parquet
            times = []
            for i in range(3):
                start = time.time()
                table = pq.read_table(parquet_path)
                df = table.to_pandas()
                elapsed = time.time() - start
                times.append(elapsed)
                if i == 0:
                    print(f"  Warmup: {elapsed:.4f}s ({num_rows/elapsed:,.0f} rows/sec)")

            avg_time = sum(times[1:]) / 2
            parquet_speed = num_rows / avg_time
            print(f"  Average: {avg_time:.4f}s ({parquet_speed:,.0f} rows/sec)")

            vs_parquet = fast_speed / parquet_speed
            print(f"\n  NCF Fast vs Parquet: {vs_parquet:.2f}x")
            print(f"  NCF Regular vs Parquet: {regular_speed/parquet_speed:.2f}x")

            compression_ratio = parquet_size / ncf_size
            print(f"\n  NCF file is {compression_ratio:.2f}x smaller than Parquet")

        finally:
            if os.path.exists(parquet_path):
                os.remove(parquet_path)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"NCF Fast Reader:    {fast_speed:,.0f} rows/sec")
    print(f"NCF Regular Reader: {regular_speed:,.0f} rows/sec")
    if PARQUET:
        print(f"Parquet Reader:     {parquet_speed:,.0f} rows/sec")
    print(f"\nSpeedup: {speedup:.2f}x (Fast vs Regular)")
    if PARQUET:
        if vs_parquet > 1:
            print(f"NCF Fast is {vs_parquet:.2f}x FASTER than Parquet")
        else:
            print(f"NCF Fast is {1/vs_parquet:.2f}x slower than Parquet")

finally:
    if os.path.exists(ncf_path):
        os.remove(ncf_path)
