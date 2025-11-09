"""
Simple test to verify NCFFastReader works
"""
from tempfile import NamedTemporaryFile
import os

from ncf_rust import NCFWriter, NCFReader, NCFFastReader
from ncf_rust import NCFSchema, ColumnSchema, NCFDataType

print("Testing NCFFastReader...")

# Generate small test data
size = 100
data = {
    'id': list(range(size)),
    'value': [float(i) * 1.5 for i in range(size)],
    'name': [f'user_{i:03d}' for i in range(size)]
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
    print(f"Writing {size} rows...")
    writer = NCFWriter(tmp_path, schema)
    writer.write(data)
    writer.close()
    print(f"File size: {os.path.getsize(tmp_path):,} bytes")

    # Test Regular Reader
    print("\nRegular Reader:")
    reader = NCFReader(tmp_path)
    result = reader.read()
    print(f"  Read {len(result['id'])} rows")
    print(f"  First ID: {result['id'][0]}, Last ID: {result['id'][-1]}")

    # Test Fast Reader
    print("\nFast Reader:")
    reader = NCFFastReader(tmp_path)
    result = reader.read()
    print(f"  Read {len(result['id'])} rows")
    print(f"  First ID: {result['id'][0]}, Last ID: {result['id'][-1]}")

    print("\n✓ SUCCESS: NCFFastReader works!")

finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
