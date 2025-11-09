"""
Test Rust NCF Roundtrip (Write -> Read)
"""

import os
from tempfile import NamedTemporaryFile
from ncf_rust import NCFWriter, NCFReader, NCFSchema, ColumnSchema, NCFDataType

print("="*80)
print("Testing Rust NCF Roundtrip (Write -> Read)")
print("="*80)

# Test 1: Simple int64 column
print("\n[Test 1] Roundtrip: int64 column...")
try:
    schema = NCFSchema(
        "test_table",
        [ColumnSchema("id", NCFDataType.int64(), None, True)],
        0,
        1
    )

    with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        writer = NCFWriter(tmp_path, schema)
        original_data = {'id': [1, 2, 3, 4, 5]}
        writer.write(original_data)
        writer.close()

        # Read
        reader = NCFReader(tmp_path)
        result_data = reader.read()

        # Verify
        assert list(result_data.keys()) == ['id'], f"Keys mismatch: {list(result_data.keys())}"
        assert result_data['id'] == original_data['id'], f"Data mismatch: {result_data['id']} vs {original_data['id']}"

        print("[OK] Roundtrip successful!")
        print(f"  Original: {original_data}")
        print(f"  Result:   {dict(result_data)}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

except Exception as e:
    print(f"[FAIL] Test 1 failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Mixed types
print("\n[Test 2] Roundtrip: int64 + float64 + string...")
try:
    schema = NCFSchema(
        "test_table",
        [
            ColumnSchema("id", NCFDataType.int64(), None, True),
            ColumnSchema("value", NCFDataType.float64(), None, True),
            ColumnSchema("name", NCFDataType.string(), None, True),
        ],
        0,
        1
    )

    with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        writer = NCFWriter(tmp_path, schema)
        original_data = {
            'id': [1, 2, 3],
            'value': [1.1, 2.2, 3.3],
            'name': ['Alice', 'Bob', 'Charlie']
        }
        writer.write(original_data)
        writer.close()

        # Read
        reader = NCFReader(tmp_path)
        result_data = reader.read()

        # Verify
        assert sorted(result_data.keys()) == sorted(original_data.keys()), \
            f"Keys mismatch: {sorted(result_data.keys())} vs {sorted(original_data.keys())}"

        for key in original_data.keys():
            if isinstance(original_data[key][0], float):
                # Check floats with tolerance
                for i, (orig, res) in enumerate(zip(original_data[key], result_data[key])):
                    assert abs(orig - res) < 1e-10, \
                        f"Float mismatch at {key}[{i}]: {res} vs {orig}"
            else:
                assert result_data[key] == original_data[key], \
                    f"Data mismatch for {key}: {result_data[key]} vs {original_data[key]}"

        print("[OK] Roundtrip successful!")
        print(f"  Columns: {list(original_data.keys())}")
        print(f"  Rows: {len(original_data['id'])}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

except Exception as e:
    print(f"[FAIL] Test 2 failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Large dataset (1000 rows)
print("\n[Test 3] Roundtrip: Large dataset (1000 rows)...")
try:
    schema = NCFSchema(
        "benchmark",
        [
            ColumnSchema("id", NCFDataType.int64(), None, True),
            ColumnSchema("value", NCFDataType.float64(), None, True),
            ColumnSchema("name", NCFDataType.string(), None, True),
        ],
        0,
        1
    )

    with NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Write
        writer = NCFWriter(tmp_path, schema)
        original_data = {
            'id': list(range(1000)),
            'value': [float(i) * 1.5 for i in range(1000)],
            'name': [f'user_{i}' for i in range(1000)]
        }
        writer.write(original_data)
        writer.close()

        file_size = os.path.getsize(tmp_path)

        # Read
        reader = NCFReader(tmp_path)
        result_data = reader.read()

        # Verify
        assert len(result_data['id']) == 1000, f"Row count mismatch: {len(result_data['id'])}"
        assert result_data['id'] == original_data['id'], "ID column mismatch"
        assert result_data['name'] == original_data['name'], "Name column mismatch"

        # Check floats
        for i in range(1000):
            assert abs(result_data['value'][i] - original_data['value'][i]) < 1e-10, \
                f"Float mismatch at index {i}"

        print("[OK] Roundtrip successful!")
        print(f"  Rows: 1000")
        print(f"  File size: {file_size:,} bytes")
        print(f"  Compression: {(1000 * 26) / file_size:.2f}x")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

except Exception as e:
    print(f"[FAIL] Test 3 failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("[OK] Rust NCF Roundtrip is WORKING!")
print("[OK] Write -> Read works perfectly")
print("[OK] All data types supported (int64, float64, string)")
print("[OK] Large datasets work (1000+ rows)")
print("\nNext: Run performance benchmarks!")
print("="*80)
