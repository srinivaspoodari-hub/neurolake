"""
Debug script to isolate the reader bug with large datasets
"""

import numpy as np
import pandas as pd
import tempfile
import os

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType

def test_dataset_size(num_rows, test_name):
    """Test with specific dataset size"""
    print(f"\n{'='*60}")
    print(f"Testing {test_name}: {num_rows:,} rows")
    print('='*60)

    # Create test data
    data = pd.DataFrame({
        "id": range(num_rows),
        "category": np.random.choice(["A", "B", "C"], num_rows),
        "name": [f"User_{i}" for i in range(num_rows)],
    })

    print(f"Input shape: {data.shape}")
    print(f"Column lengths: id={len(data['id'])}, category={len(data['category'])}, name={len(data['name'])}")

    # Create schema
    schema = NCFSchema(
        table_name="debug",
        columns=[
            ColumnSchema(name="id", data_type=NCFDataType.INT64),
            ColumnSchema(name="category", data_type=NCFDataType.STRING),
            ColumnSchema(name="name", data_type=NCFDataType.STRING),
        ]
    )

    # Write
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        print(f"\nWriting to {tmp_path}...")
        with NCFWriter(tmp_path, schema) as writer:
            writer.write(data)

        file_size = os.path.getsize(tmp_path)
        print(f"File written: {file_size:,} bytes")

        # Read with detailed logging
        print(f"\nReading from {tmp_path}...")
        with NCFReader(tmp_path) as reader:
            print(f"Schema loaded: {reader.schema.column_names()}")
            print(f"Row count from header: {reader.row_count}")

            # Read columns individually to see which one fails
            column_data = {}
            for col_name in ["id", "category", "name"]:
                print(f"\n  Reading column '{col_name}'...")
                try:
                    col_dict = reader._read_columns([col_name], None)
                    col_array = col_dict[col_name]
                    print(f"    Length: {len(col_array)}, dtype: {col_array.dtype}")
                    if len(col_array) < 10:
                        print(f"    Values: {list(col_array)}")
                    else:
                        print(f"    First 5: {list(col_array[:5])}")
                        print(f"    Last 5: {list(col_array[-5:])}")
                    column_data[col_name] = col_array
                except Exception as e:
                    print(f"    ERROR reading column '{col_name}': {e}")
                    import traceback
                    traceback.print_exc()
                    return False

            # Check lengths
            print(f"\nColumn length check:")
            for col_name, col_array in column_data.items():
                print(f"  {col_name}: {len(col_array)} rows")

            # Try to create DataFrame
            print(f"\nCreating DataFrame...")
            try:
                result = pd.DataFrame(column_data)
                print(f"SUCCESS! Result shape: {result.shape}")

                # Verify data
                if len(result) != len(data):
                    print(f"WARNING: Row count mismatch: {len(result)} != {len(data)}")
                    return False

                print(f"[PASS] Test passed!")
                return True

            except Exception as e:
                print(f"ERROR creating DataFrame: {e}")
                return False

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    # Test with increasing dataset sizes to find the threshold
    sizes = [
        (100, "Small"),
        (1000, "Medium"),
        (10000, "Large"),
        (50000, "Very Large"),
        (100000, "Huge"),
    ]

    results = []
    for num_rows, name in sizes:
        success = test_dataset_size(num_rows, name)
        results.append((num_rows, name, success))

        if not success:
            print(f"\n[FAIL] Failed at {num_rows:,} rows!")
            print("Stopping tests here to investigate.")
            break

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for num_rows, name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}: {num_rows:,} rows")
