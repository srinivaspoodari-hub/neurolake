"""
Debug the exact benchmark dataset structure
"""

import numpy as np
import pandas as pd
import tempfile
import os

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType, SemanticType

# Create EXACT benchmark dataset
num_rows = 1000  # Start small

print(f"Creating benchmark dataset with {num_rows:,} rows...")
data = pd.DataFrame({
    "id": range(num_rows),
    "value": np.random.rand(num_rows),
    "category": np.random.choice(["A", "B", "C", "D", "E"], num_rows),
    "score": np.random.randint(0, 100, num_rows),
    "name": [f"User_{i}" for i in range(num_rows)],
    "email": [f"user{i}@example.com" for i in range(num_rows)],
})

print(f"Dataset shape: {data.shape}")
print(f"Columns: {list(data.columns)}")
print(f"Dtypes:\n{data.dtypes}")

# Create EXACT schema from benchmark
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

# Write
with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
    tmp_path = tmp.name

try:
    print(f"\nWriting to {tmp_path}...")
    with NCFWriter(tmp_path, schema) as writer:
        writer.write(data)

    file_size = os.path.getsize(tmp_path)
    print(f"File written: {file_size:,} bytes")

    # Read back
    print(f"\nReading back...")
    with NCFReader(tmp_path) as reader:
        print(f"Schema: {reader.schema.column_names()}")
        print(f"Row count: {reader.row_count}")

        # Read each column individually
        print(f"\nReading columns individually:")
        column_data = {}
        for col_name in data.columns:
            print(f"  {col_name}...", end=" ")
            col_dict = reader._read_columns([col_name], None)
            col_array = col_dict[col_name]
            print(f"length={len(col_array)}, dtype={col_array.dtype}")
            column_data[col_name] = col_array

        # Check all lengths
        print(f"\nLength check:")
        for col_name, col_array in column_data.items():
            print(f"  {col_name}: {len(col_array)}")

        # Try to create DataFrame
        print(f"\nCreating DataFrame from columns...")
        result = pd.DataFrame(column_data)
        print(f"SUCCESS! Shape: {result.shape}")
        print(f"\nFirst 5 rows:")
        print(result.head())

        # Now try with reader.read() directly
        print(f"\nTrying reader.read() directly...")
        result2 = reader.read()
        print(f"SUCCESS! Shape: {result2.shape}")
        print(f"\nFirst 5 rows:")
        print(result2.head())

finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

print("\n[SUCCESS] All tests passed!")
