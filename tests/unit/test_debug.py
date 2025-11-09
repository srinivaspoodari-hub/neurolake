import numpy as np
import pandas as pd
import tempfile

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType

# Create small test data
data = pd.DataFrame({
    "id": range(100),
    "category": np.random.choice(["A", "B", "C"], 100),
    "name": [f"User_{i}" for i in range(100)],
})

print(f"Input data shape: {data.shape}")
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

with NCFWriter(tmp_path, schema) as writer:
    writer.write(data)

print(f"Wrote to {tmp_path}")

# Read
with NCFReader(tmp_path) as reader:
    column_data = reader._read_columns(["id", "category", "name"], None)

    print(f"\nRead columns:")
    for col_name, col_array in column_data.items():
        print(f"  {col_name}: length={len(col_array)}, dtype={col_array.dtype}")
        if len(col_array) < 10:
            print(f"    values={list(col_array)}")
        else:
            print(f"    first 5={list(col_array[:5])}")
