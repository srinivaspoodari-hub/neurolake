"""
Test NCFFastReader with larger dataset to see parallel speedup
"""
import time
from tempfile import NamedTemporaryFile
import os

from ncf_rust import NCFWriter, NCFReader, NCFFastReader
from ncf_rust import NCFSchema, ColumnSchema, NCFDataType

print("NCF Fast Reader - Large Dataset Test")
print("=" * 60)

# Test different sizes
sizes = [100_000, 500_000, 1_000_000]

for size in sizes:
    print(f"\nTesting with {size:,} rows...")

    # Generate test data
    data = {
        'id': list(range(size)),
        'value': [float(i) * 1.5 for i in range(size)],
        'score': [float(i) * 2.3 for i in range(size)],
        'name': [f'user_{i:06d}' for i in range(size)]
    }

    # Create schema
    schema = NCFSchema("test", [
        ColumnSchema("id", NCFDataType.int64(), None, True),
        ColumnSchema("value", NCFDataType.float64(), None, True),
        ColumnSchema("score", NCFDataType.float64(), None, True),
        ColumnSchema("name", NCFDataType.string(), None, True),
    ], 0, 1)

    # Write file
    with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        writer = NCFWriter(tmp_path, schema)
        write_start = time.time()
        writer.write(data)
        writer.close()
        write_time = time.time() - write_start
        write_speed = size / write_time

        file_size = os.path.getsize(tmp_path)
        print(f"  File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"  Write speed: {write_speed:,.0f} rows/sec")

        # Test Regular Reader (3 runs)
        regular_times = []
        for _ in range(3):
            reader = NCFReader(tmp_path)
            start = time.time()
            result = reader.read()
            elapsed = time.time() - start
            regular_times.append(elapsed)

        avg_regular = sum(regular_times) / len(regular_times)
        regular_speed = size / avg_regular
        print(f"\n  [Regular Reader]")
        print(f"    Time: {avg_regular:.4f}s")
        print(f"    Speed: {regular_speed:,.0f} rows/sec")

        # Test Fast Reader (3 runs)
        fast_times = []
        for _ in range(3):
            reader = NCFFastReader(tmp_path)
            start = time.time()
            result = reader.read()
            elapsed = time.time() - start
            fast_times.append(elapsed)

        avg_fast = sum(fast_times) / len(fast_times)
        fast_speed = size / avg_fast
        print(f"\n  [Fast Reader (Parallel)]")
        print(f"    Time: {avg_fast:.4f}s")
        print(f"    Speed: {fast_speed:,.0f} rows/sec")

        # Calculate speedup
        speedup = fast_speed / regular_speed
        print(f"\n  Speedup: {speedup:.2f}x")

        if speedup > 1.5:
            print(f"  Status: EXCELLENT (>1.5x speedup)")
        elif speedup > 1.2:
            print(f"  Status: GOOD (>1.2x speedup)")
        else:
            print(f"  Status: Minimal speedup (dataset may be too small)")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

print("\n" + "=" * 60)
print("Test complete!")
