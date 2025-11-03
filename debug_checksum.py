"""
Debug checksum validation
"""

import numpy as np
import pandas as pd
import tempfile
import os
import hashlib

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType

# Create small test data
data = pd.DataFrame({
    "id": range(10),
    "value": np.random.rand(10),
})

schema = NCFSchema(
    table_name="checksum_test",
    columns=[
        ColumnSchema(name="id", data_type=NCFDataType.INT64),
        ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
    ]
)

# Write
with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
    tmp_path = tmp.name

try:
    print(f"Writing to {tmp_path}...")
    with NCFWriter(tmp_path, schema) as writer:
        writer.write(data)

    print(f"File size: {os.path.getsize(tmp_path)} bytes")

    # Read and check checksum
    print(f"\nReading and validating checksum...")
    with NCFReader(tmp_path) as reader:
        print(f"Footer offset: {reader.offsets['footer']}")

        # Try checksum validation
        print(f"\nAttempting checksum validation...")
        is_valid = reader.validate_checksum()
        print(f"Checksum valid: {is_valid}")

        if not is_valid:
            # Debug: manually calculate checksums
            print(f"\n[DEBUG] Manual checksum calculation:")

            reader.file_handle.seek(reader.offsets["footer"])
            footer_magic = reader.file_handle.read(4)
            print(f"Footer magic: {footer_magic}")

            footer_version = reader.file_handle.read(4)
            print(f"Footer version: {footer_version}")

            checksum_type = reader.file_handle.read(1)
            print(f"Checksum type: {checksum_type[0]}")

            stored_checksum = reader.file_handle.read(32)
            print(f"Stored checksum (hex): {stored_checksum.hex()}")

            # Calculate checksum
            reader.file_handle.seek(0)
            hasher = hashlib.sha256()
            bytes_to_hash = reader.offsets["footer"]
            print(f"Bytes to hash: {bytes_to_hash}")

            data_to_hash = reader.file_handle.read(bytes_to_hash)
            print(f"Actually read: {len(data_to_hash)} bytes")

            hasher.update(data_to_hash)
            calculated_checksum = hasher.digest()
            print(f"Calculated checksum (hex): {calculated_checksum.hex()}")

            print(f"\nChecksums match: {stored_checksum == calculated_checksum}")

finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
