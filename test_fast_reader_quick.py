"""
Quick test of NCFFastReader
"""
import time
from tempfile import NamedTemporaryFile
import os

from ncf_rust import NCFWriter, NCFReader, NCFFastReader
from ncf_rust import NCFSchema, ColumnSchema, NCFDataType

print("Quick Fast Reader Test")
print("=" * 60)

# Generate test data
size = 10_000
data = {
    'id': list(range(size)),
    'value': [float(i) * 1.5 for i in range(size)],
    'name': [f'user_{i:06d}' for i in range(size)]
}

# Create schema
schema = NCFSchema("test", [
    ColumnSchema("id", NCFDataType.int64(), None, True),
    ColumnSchema("value", NCFDataType.float64(), None, True),
    ColumnSchema("name", NCFDataType.string(), None, True),
], 0, 1)

# Write file
with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
    tmp_path = tmp.name

try:
    writer = NCFWriter(tmp_path, schema)
    writer.write(data)
    writer.close()

    print(f"\nCreated test file: {size:,} rows")
    print(f"File size: {os.path.getsize(tmp_path):,} bytes")

    # Test Regular Reader
    print("\n[Regular Reader]")
    times = []
    for _ in range(3):
        reader = NCFReader(tmp_path)
        start = time.time()
        result = reader.read()
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    regular_speed = size / avg_time
    print(f"  Average time: {avg_time:.4f}s")
    print(f"  Speed: {regular_speed:,.0f} rows/sec")

    # Test Fast Reader
    print("\n[Fast Reader (Parallel)]")
    times = []
    for _ in range(3):
        reader = NCFFastReader(tmp_path)
        start = time.time()
        result = reader.read()
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    fast_speed = size / avg_time
    print(f"  Average time: {avg_time:.4f}s")
    print(f"  Speed: {fast_speed:,.0f} rows/sec")

    # Calculate speedup
    speedup = fast_speed / regular_speed
    print(f"\n{'=' * 60}")
    print(f"Speedup: {speedup:.2f}x faster")
    print(f"{'=' * 60}")

    # Verify correctness
    assert len(result['id']) == size
    assert result['id'][0] == 0
    assert result['id'][-1] == size - 1
    print("\n✓ Correctness verified")

finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

print("\nTest complete!")
