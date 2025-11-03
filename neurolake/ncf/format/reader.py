"""
NCF Reader

Reads data from NCF format files with decompression and column-major parsing.

Features (v1.0):
- File parsing and validation
- Schema deserialization
- ZSTD decompression
- Column-major to row-major conversion
- Statistics access
- Column projection (read specific columns)
"""

from pathlib import Path
from typing import Union, List, Optional, Dict, Any
import struct
import hashlib

import numpy as np
import msgpack
import zstandard as zstd

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False

from neurolake.ncf.format.schema import NCFSchema, ColumnStatistics, NCFDataType


# NCF Magic Numbers
NCF_MAGIC = b"NCF\x01"
NCF_FOOTER_MAGIC = b"NCFE"

# Compression types
COMPRESSION_NONE = 0
COMPRESSION_ZSTD = 1
COMPRESSION_LZ4 = 2
COMPRESSION_NEURAL = 3


class NCFReader:
    """
    Reads data from NCF format files

    Example:
        reader = NCFReader("input.ncf")
        df = reader.read()  # Read all data

        # Or read specific columns
        df = reader.read(columns=["id", "name"])

        # Just read schema
        schema = reader.read_schema()

        reader.close()
    """

    def __init__(self, path: Union[str, Path]):
        """
        Initialize NCF reader

        Args:
            path: Input file path (.ncf extension)
        """
        self.path = Path(path)
        self.file_handle = None
        self.schema: Optional[NCFSchema] = None
        self.statistics: Optional[Dict[str, ColumnStatistics]] = None
        self.offsets: Dict[str, int] = {}
        self._open()

    def _open(self):
        """Open file for reading"""
        if not self.path.exists():
            raise FileNotFoundError(f"NCF file not found: {self.path}")

        self.file_handle = open(self.path, "rb")
        self._read_and_validate_header()
        self._read_schema()
        self._read_statistics()

    def _read_and_validate_header(self):
        """Read and validate NCF magic number, version, and header"""
        # Read magic number
        magic = self.file_handle.read(4)
        if magic != NCF_MAGIC:
            raise ValueError(f"Invalid NCF file: {self.path} (bad magic number)")

        # Read version
        version_bytes = self.file_handle.read(4)
        version = struct.unpack("<I", version_bytes)[0]
        if version != 1:
            raise ValueError(f"Unsupported NCF version: {version}")

        # Read header (60 bytes)
        # Format: 5 uint32 (I) = 20 bytes, 3 uint64 (Q) = 24 bytes, 2 uint8 (B) = 2 bytes, 14 bytes padding
        header_data = self.file_handle.read(60)
        header = struct.unpack("<IIIIIQQQBB14x", header_data)

        self.header = {
            "schema_offset": header[0],
            "stats_offset": header[1],
            "indexes_offset": header[2],
            "data_offset": header[3],
            "footer_offset": header[4],
            "row_count": header[5],
            "created_timestamp": header[6],
            "modified_timestamp": header[7],
            "compression_type": header[8],
            "encryption_enabled": header[9],
        }

        # Store offsets
        self.offsets["schema"] = self.header["schema_offset"]
        self.offsets["stats"] = self.header["stats_offset"]
        self.offsets["data"] = self.header["data_offset"]
        self.offsets["footer"] = self.header["footer_offset"]
        self.row_count = self.header["row_count"]

    def _read_schema(self):
        """Read and deserialize schema"""
        # Seek to schema offset
        self.file_handle.seek(self.offsets["schema"])

        # Read schema length
        schema_length = struct.unpack("<I", self.file_handle.read(4))[0]

        # Read schema bytes
        schema_bytes = self.file_handle.read(schema_length)

        # Deserialize from msgpack
        schema_dict = msgpack.unpackb(schema_bytes, raw=False)
        self.schema = NCFSchema.from_dict(schema_dict)

    def _read_statistics(self):
        """Read column statistics"""
        # Seek to statistics offset
        self.file_handle.seek(self.offsets["stats"])

        # Read statistics length
        stats_length = struct.unpack("<I", self.file_handle.read(4))[0]

        # Read statistics bytes
        stats_bytes = self.file_handle.read(stats_length)

        # Deserialize from msgpack
        stats_dict = msgpack.unpackb(stats_bytes, raw=False)

        # Convert to ColumnStatistics objects
        self.statistics = {}
        for col_name, stats in stats_dict.items():
            self.statistics[col_name] = ColumnStatistics(
                min_value=stats.get("min_value"),
                max_value=stats.get("max_value"),
                null_count=stats.get("null_count", 0),
                distinct_count=stats.get("distinct_count"),
                total_count=stats.get("total_count", 0),
                avg_length=stats.get("avg_length"),
            )

    def read(
        self,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        return_type: str = "pandas"
    ):
        """
        Read data from NCF file

        Args:
            columns: List of columns to read (None = all)
            limit: Maximum rows to read (None = all)
            return_type: "pandas", "polars", or "dict"

        Returns:
            DataFrame or dict with requested data
        """
        # Default to all columns
        if columns is None:
            columns = self.schema.column_names()

        # Validate columns exist
        for col in columns:
            if self.schema.get_column(col) is None:
                raise ValueError(f"Column not found in schema: {col}")

        # Read column data
        column_data = self._read_columns(columns, limit)

        # Convert to requested format
        if return_type == "pandas":
            if not HAS_PANDAS:
                raise ImportError("pandas not installed")
            return pd.DataFrame(column_data)

        elif return_type == "polars":
            if not HAS_POLARS:
                raise ImportError("polars not installed")
            return pl.DataFrame(column_data)

        elif return_type == "dict":
            return column_data

        else:
            raise ValueError(f"Unknown return_type: {return_type}")

    def _read_columns(
        self, columns: List[str], limit: Optional[int]
    ) -> Dict[str, np.ndarray]:
        """Read specific columns from file"""
        # Seek to data section
        self.file_handle.seek(self.offsets["data"])

        # Read all column groups
        column_data = {}

        while self.file_handle.tell() < self.offsets["footer"]:
            # Read group header
            try:
                group_id = struct.unpack("<I", self.file_handle.read(4))[0]
                col_count = struct.unpack("<I", self.file_handle.read(4))[0]
            except struct.error:
                # End of data section
                break

            # Read columns in this group
            for _ in range(col_count):
                # Read column name (null-terminated)
                col_name_bytes = b""
                while True:
                    byte = self.file_handle.read(1)
                    if byte == b"\x00":
                        break
                    col_name_bytes += byte

                col_name = col_name_bytes.decode("utf-8")

                # Read column data size and compression type
                data_size = struct.unpack("<Q", self.file_handle.read(8))[0]
                compression_type = struct.unpack("<B", self.file_handle.read(1))[0]

                # Read compressed data
                compressed_data = self.file_handle.read(data_size)

                # Only decompress and parse if this column is requested
                if col_name in columns:
                    # Decompress
                    if compression_type == COMPRESSION_ZSTD:
                        decompressor = zstd.ZstdDecompressor()
                        decompressed = decompressor.decompress(compressed_data)
                    elif compression_type == COMPRESSION_NONE:
                        decompressed = compressed_data
                    else:
                        raise ValueError(f"Unsupported compression type: {compression_type}")

                    # Deserialize column
                    col_schema = self.schema.get_column(col_name)
                    col_array = self._deserialize_column(decompressed, col_schema, limit)
                    column_data[col_name] = col_array

        return column_data

    def _deserialize_column(
        self, data: bytes, col_schema, limit: Optional[int]
    ) -> np.ndarray:
        """Deserialize column data from bytes"""

        if col_schema.data_type in [
            NCFDataType.INT8, NCFDataType.INT16, NCFDataType.INT32, NCFDataType.INT64,
            NCFDataType.UINT8, NCFDataType.UINT16, NCFDataType.UINT32, NCFDataType.UINT64,
            NCFDataType.FLOAT32, NCFDataType.FLOAT64
        ]:
            # Fixed-width numeric types
            dtype_map = {
                NCFDataType.INT8: np.int8,
                NCFDataType.INT16: np.int16,
                NCFDataType.INT32: np.int32,
                NCFDataType.INT64: np.int64,
                NCFDataType.UINT8: np.uint8,
                NCFDataType.UINT16: np.uint16,
                NCFDataType.UINT32: np.uint32,
                NCFDataType.UINT64: np.uint64,
                NCFDataType.FLOAT32: np.float32,
                NCFDataType.FLOAT64: np.float64,
            }
            dtype = dtype_map[col_schema.data_type]
            array = np.frombuffer(data, dtype=dtype)

            if limit is not None:
                array = array[:limit]

            return array

        elif col_schema.data_type == NCFDataType.STRING:
            # Variable-width strings
            # Format: [num_strings:uint32] [offset1:uint32] [offset2] ... [data_blob]

            # Read number of strings
            num_strings = struct.unpack("<I", data[:4])[0]

            # Read offsets
            offset_size = (num_strings + 1) * 4
            offsets_data = data[4:4 + offset_size]
            offsets = struct.unpack(f"<{num_strings + 1}I", offsets_data)

            # Read string data blob
            string_data = data[4 + offset_size:]

            # Extract strings
            strings = []
            for i in range(num_strings):
                start = offsets[i]
                end = offsets[i + 1]
                s = string_data[start:end].decode("utf-8")
                strings.append(s if s else None)

            array = np.array(strings, dtype=object)

            if limit is not None:
                array = array[:limit]

            return array

        else:
            # Fallback: pickle
            import pickle
            array = pickle.loads(data)

            if limit is not None:
                array = array[:limit]

            return array

    def read_schema(self) -> NCFSchema:
        """Get schema without reading data"""
        if self.schema is None:
            raise ValueError("Schema not loaded")
        return self.schema

    def get_statistics(self, column: Optional[str] = None):
        """
        Get column statistics

        Args:
            column: Column name (None = all columns)

        Returns:
            ColumnStatistics or dict of statistics
        """
        if self.statistics is None:
            raise ValueError("Statistics not loaded")

        if column is not None:
            return self.statistics.get(column)
        else:
            return self.statistics

    def get_row_count(self) -> int:
        """Get total row count"""
        return self.row_count

    def validate_checksum(self) -> bool:
        """
        Validate file integrity using SHA-256 checksum

        Returns:
            True if checksum is valid, False otherwise
        """
        # Seek to footer
        self.file_handle.seek(self.offsets["footer"])

        # Read footer magic
        footer_magic = self.file_handle.read(4)
        if footer_magic != NCF_FOOTER_MAGIC:
            return False

        # Read footer version
        footer_version = struct.unpack("<I", self.file_handle.read(4))[0]

        # Read checksum type
        checksum_type = struct.unpack("<B", self.file_handle.read(1))[0]
        if checksum_type != 2:  # SHA-256
            return False

        # Read stored checksum
        stored_checksum = self.file_handle.read(32)

        # Calculate actual checksum
        self.file_handle.seek(0)
        hasher = hashlib.sha256()

        bytes_to_hash = self.offsets["footer"]
        chunk_size = 1024 * 1024

        bytes_read = 0
        while bytes_read < bytes_to_hash:
            to_read = min(chunk_size, bytes_to_hash - bytes_read)
            chunk = self.file_handle.read(to_read)
            if not chunk:
                break
            hasher.update(chunk)
            bytes_read += len(chunk)

        calculated_checksum = hasher.digest()

        return stored_checksum == calculated_checksum

    def close(self):
        """Close the NCF file"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __repr__(self):
        if self.schema:
            return f"NCFReader('{self.path}', rows={self.row_count}, cols={len(self.schema.columns)})"
        return f"NCFReader('{self.path}')"


# Example usage
if __name__ == "__main__":
    import sys

    print("NCF Reader - Basic Implementation")
    print("=" * 50)

    # Check if test file exists
    test_file = "test_output.ncf"

    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        print("Run writer.py first to create a test file.")
        sys.exit(1)

    # Open and read NCF file
    print(f"\nReading {test_file}...")

    with NCFReader(test_file) as reader:
        # Read schema
        schema = reader.read_schema()
        print(f"\n✓ Schema loaded:")
        print(f"  Table: {schema.table_name}")
        print(f"  Columns: {schema.column_names()}")
        print(f"  Row count: {reader.get_row_count()}")

        # Read statistics
        print(f"\n✓ Statistics:")
        for col_name in schema.column_names():
            stats = reader.get_statistics(col_name)
            if stats:
                print(f"  {col_name}: min={stats.min_value}, max={stats.max_value}, nulls={stats.null_count}")

        # Validate checksum
        print(f"\n✓ Validating checksum...")
        if reader.validate_checksum():
            print("  ✓ Checksum valid")
        else:
            print("  ❌ Checksum invalid!")

        # Read all data
        print(f"\n✓ Reading all data...")
        df = reader.read()
        print(f"  Shape: {df.shape}")
        print(f"\nFirst 5 rows:")
        print(df.head())

        # Read specific columns
        print(f"\n✓ Reading specific columns (id, name)...")
        df_subset = reader.read(columns=["id", "name"], limit=10)
        print(df_subset)

    print("\n✓ NCF Reader implementation complete!")
