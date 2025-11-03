"""
NCF Writer

Writes data to NCF format files with basic compression and column-major layout.

Features (v1.0):
- Column-major storage
- ZSTD compression
- Schema serialization
- Statistics generation
- Column grouping
"""

from pathlib import Path
from typing import Union, Dict, Any, Optional
import struct
import time
import hashlib
from datetime import datetime

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

from neurolake.ncf.format.schema import (
    NCFSchema, ColumnSchema, ColumnStatistics, NCFDataType
)


# NCF Magic Numbers
NCF_MAGIC = b"NCF\x01"
NCF_FOOTER_MAGIC = b"NCFE"
NCF_VERSION = 1

# Compression types
COMPRESSION_NONE = 0
COMPRESSION_ZSTD = 1
COMPRESSION_LZ4 = 2
COMPRESSION_NEURAL = 3


class NCFWriter:
    """
    Writes data to NCF format files

    Example:
        from neurolake.ncf import NCFWriter, NCFSchema, ColumnSchema, NCFDataType

        schema = NCFSchema(
            table_name="users",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ]
        )

        writer = NCFWriter("output.ncf", schema)
        writer.write(dataframe)
        writer.close()
    """

    def __init__(
        self,
        path: Union[str, Path],
        schema: NCFSchema,
        compression: str = "zstd",
        compression_level: int = 3
    ):
        """
        Initialize NCF writer

        Args:
            path: Output file path (.ncf extension)
            schema: NCF schema defining the table structure
            compression: Compression algorithm ("none", "zstd", "lz4")
            compression_level: Compression level (1-22 for zstd)
        """
        self.path = Path(path)
        self.schema = schema
        self.compression = compression
        self.compression_level = compression_level
        self.file_handle = None
        self.offsets: Dict[str, int] = {}
        self.data_written = False

        # Compression setup
        if compression == "zstd":
            self.compressor = zstd.ZstdCompressor(level=compression_level)
            self.compression_type = COMPRESSION_ZSTD
        else:
            self.compressor = None
            self.compression_type = COMPRESSION_NONE

    def _open(self):
        """Open file for writing"""
        self.file_handle = open(self.path, "w+b")
        self._write_magic_and_version()
        self._write_placeholder_header()

    def _write_magic_and_version(self):
        """Write NCF magic number and version"""
        self.file_handle.write(NCF_MAGIC)
        self.file_handle.write(struct.pack("<I", NCF_VERSION))

    def _write_placeholder_header(self):
        """Write placeholder header (will be updated later with correct offsets)"""
        # Reserve 60 bytes for header
        self.offsets["header_start"] = self.file_handle.tell()
        self.file_handle.write(b"\x00" * 60)

    def write(self, data: Any):
        """
        Write data to NCF file

        Args:
            data: DataFrame (pandas/polars) or dict of columns

        Raises:
            ValueError: If data format is unsupported or doesn't match schema
        """
        if self.data_written:
            raise ValueError("Data already written. NCF files are write-once.")

        if self.file_handle is None:
            self._open()

        # Convert data to column dict
        columns = self._convert_to_columns(data)

        # Update schema with row count
        row_count = len(next(iter(columns.values())))
        self.schema.row_count = row_count

        # Generate statistics
        statistics = self._generate_statistics(columns)

        # Write schema
        self._write_schema()

        # Write statistics
        self._write_statistics(statistics)

        # Write column data
        self._write_column_data(columns)

        # Record footer position
        self.offsets["footer_start"] = self.file_handle.tell()

        # Update header with correct offsets (including footer offset)
        self._update_header(row_count)

        # Write footer with checksum (calculated from finalized header)
        self._write_footer()

        self.data_written = True

    def _convert_to_columns(self, data: Any) -> Dict[str, np.ndarray]:
        """Convert input data to column dictionary"""
        if isinstance(data, dict):
            # Already in column format
            return {k: np.array(v) for k, v in data.items()}

        elif HAS_PANDAS and isinstance(data, pd.DataFrame):
            # Pandas DataFrame
            return {col: data[col].to_numpy() for col in data.columns}

        elif HAS_POLARS and isinstance(data, pl.DataFrame):
            # Polars DataFrame
            return {col: data[col].to_numpy() for col in data.columns}

        else:
            raise ValueError(
                f"Unsupported data type: {type(data)}. "
                "Use pandas.DataFrame, polars.DataFrame, or dict of columns."
            )

    def _generate_statistics(
        self, columns: Dict[str, np.ndarray]
    ) -> Dict[str, ColumnStatistics]:
        """Generate statistics for each column"""
        stats = {}

        for col_name, col_data in columns.items():
            col_schema = self.schema.get_column(col_name)
            if not col_schema:
                continue

            # Calculate basic statistics
            null_count = int(np.sum(pd.isna(col_data)) if HAS_PANDAS else 0)
            total_count = len(col_data)

            # Min/max (for comparable types)
            try:
                non_null = col_data[~pd.isna(col_data)] if HAS_PANDAS else col_data
                min_val = np.min(non_null) if len(non_null) > 0 else None
                max_val = np.max(non_null) if len(non_null) > 0 else None
            except (TypeError, ValueError):
                min_val = None
                max_val = None

            # Distinct count (approximate)
            try:
                distinct_count = len(np.unique(col_data))
            except TypeError:
                distinct_count = None

            # Avg length for strings
            avg_length = None
            if col_schema.data_type == NCFDataType.STRING:
                lengths = [len(str(x)) for x in col_data if x is not None]
                avg_length = np.mean(lengths) if lengths else None

            stats[col_name] = ColumnStatistics(
                min_value=min_val,
                max_value=max_val,
                null_count=null_count,
                distinct_count=distinct_count,
                total_count=total_count,
                avg_length=avg_length
            )

        return stats

    def _write_schema(self):
        """Write schema to file"""
        self.offsets["schema_start"] = self.file_handle.tell()

        # Serialize schema to msgpack
        schema_dict = self.schema.to_dict()
        schema_bytes = msgpack.packb(schema_dict)

        # Write schema length and data
        self.file_handle.write(struct.pack("<I", len(schema_bytes)))
        self.file_handle.write(schema_bytes)

        self.offsets["schema_end"] = self.file_handle.tell()

    def _write_statistics(self, statistics: Dict[str, ColumnStatistics]):
        """Write statistics block"""
        self.offsets["stats_start"] = self.file_handle.tell()

        # Serialize statistics to msgpack
        stats_dict = {
            name: stats.to_dict() for name, stats in statistics.items()
        }
        stats_bytes = msgpack.packb(stats_dict)

        # Write statistics length and data
        self.file_handle.write(struct.pack("<I", len(stats_bytes)))
        self.file_handle.write(stats_bytes)

        self.offsets["stats_end"] = self.file_handle.tell()

    def _write_column_data(self, columns: Dict[str, np.ndarray]):
        """Write column data in column groups"""
        self.offsets["data_start"] = self.file_handle.tell()

        # Group columns by column_group setting
        groups = self._organize_column_groups(columns)

        # Write each group
        for group_id, group_columns in groups.items():
            self._write_column_group(group_id, group_columns, columns)

        self.offsets["data_end"] = self.file_handle.tell()

    def _organize_column_groups(
        self, columns: Dict[str, np.ndarray]
    ) -> Dict[int, list]:
        """Organize columns into groups"""
        groups: Dict[int, list] = {}

        for col_name in columns.keys():
            col_schema = self.schema.get_column(col_name)
            if not col_schema:
                continue

            group_id = col_schema.column_group if col_schema.column_group is not None else 0

            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(col_name)

        return groups

    def _write_column_group(
        self,
        group_id: int,
        group_columns: list,
        all_columns: Dict[str, np.ndarray]
    ):
        """Write a single column group"""
        # Write group header
        self.file_handle.write(struct.pack("<I", group_id))
        self.file_handle.write(struct.pack("<I", len(group_columns)))

        # Write each column in the group
        for col_name in group_columns:
            col_data = all_columns[col_name]
            col_schema = self.schema.get_column(col_name)

            # Write column name (null-terminated)
            name_bytes = col_name.encode("utf-8") + b"\x00"
            self.file_handle.write(name_bytes)

            # Serialize column data
            serialized = self._serialize_column(col_data, col_schema)

            # Compress if enabled
            if self.compressor:
                compressed = self.compressor.compress(serialized)
            else:
                compressed = serialized

            # Write column data
            self.file_handle.write(struct.pack("<Q", len(compressed)))
            self.file_handle.write(struct.pack("<B", self.compression_type))
            self.file_handle.write(compressed)

    def _serialize_column(
        self, col_data: np.ndarray, col_schema: ColumnSchema
    ) -> bytes:
        """Serialize column data to bytes"""
        # For now, use simple numpy serialization
        # TODO: Implement proper NCF column encoding (null bitmaps, dictionaries, etc.)

        # Convert to bytes
        if col_schema.data_type in [
            NCFDataType.INT8, NCFDataType.INT16, NCFDataType.INT32, NCFDataType.INT64,
            NCFDataType.UINT8, NCFDataType.UINT16, NCFDataType.UINT32, NCFDataType.UINT64,
            NCFDataType.FLOAT32, NCFDataType.FLOAT64
        ]:
            # Fixed-width numeric types
            # IMPORTANT: Convert to target dtype before serialization
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
            target_dtype = dtype_map[col_schema.data_type]
            col_data_typed = col_data.astype(target_dtype)
            return col_data_typed.tobytes()

        elif col_schema.data_type == NCFDataType.STRING:
            # Variable-width strings
            # Format: [num_strings:uint32] [offset1:uint32] [offset2] ... [data_blob]
            strings = [str(x).encode("utf-8") if x is not None else b"" for x in col_data]

            # Build offset array
            offsets = [0]
            for s in strings:
                offsets.append(offsets[-1] + len(s))

            # Serialize
            result = struct.pack("<I", len(strings))
            result += struct.pack(f"<{len(offsets)}I", *offsets)
            result += b"".join(strings)

            return result

        else:
            # Fallback: pickle
            import pickle
            return pickle.dumps(col_data)

    def _write_footer(self):
        """Write footer with checksum and offset index"""
        # Footer position already recorded before header update
        # Seek to footer position
        self.file_handle.seek(self.offsets["footer_start"])

        # Calculate checksum of entire file (except footer)
        self.file_handle.flush()
        self.file_handle.seek(0)
        hasher = hashlib.sha256()

        # Read and hash everything before footer
        bytes_to_hash = self.offsets["footer_start"]
        chunk_size = 1024 * 1024  # 1MB chunks

        bytes_read = 0
        while bytes_read < bytes_to_hash:
            to_read = min(chunk_size, bytes_to_hash - bytes_read)
            chunk = self.file_handle.read(to_read)
            if not chunk:
                break
            hasher.update(chunk)
            bytes_read += len(chunk)

        checksum = hasher.digest()

        # Seek to footer position
        self.file_handle.seek(self.offsets["footer_start"])

        # Write footer magic
        self.file_handle.write(NCF_FOOTER_MAGIC)

        # Write footer version
        self.file_handle.write(struct.pack("<I", 1))

        # Write checksum type (2 = SHA-256)
        self.file_handle.write(struct.pack("<B", 2))

        # Write checksum
        self.file_handle.write(checksum)

        # Write offset index
        offset_entries = [
            ("header", self.offsets.get("header_start", 0)),
            ("schema", self.offsets.get("schema_start", 0)),
            ("stats", self.offsets.get("stats_start", 0)),
            ("data", self.offsets.get("data_start", 0)),
            ("footer", self.offsets.get("footer_start", 0)),
        ]

        self.file_handle.write(struct.pack("<I", len(offset_entries)))

        for name, offset in offset_entries:
            name_bytes = name.encode("utf-8").ljust(16, b"\x00")[:16]
            self.file_handle.write(name_bytes)
            self.file_handle.write(struct.pack("<Q", offset))

        self.offsets["footer_end"] = self.file_handle.tell()

    def _update_header(self, row_count: int):
        """Update header with correct offsets and metadata"""
        current_pos = self.file_handle.tell()

        # Seek to header position
        self.file_handle.seek(self.offsets["header_start"])

        # Write header (60 bytes total)
        # Format: 5 uint32 (I) = 20 bytes, 3 uint64 (Q) = 24 bytes, 2 uint8 (B) = 2 bytes
        # Total without padding: 20 + 24 + 2 = 46 bytes
        # Padding needed: 60 - 46 = 14 bytes
        header = struct.pack(
            "<IIIIIQQQBB14x",
            self.offsets.get("schema_start", 0),  # Schema offset (4 bytes)
            self.offsets.get("stats_start", 0),   # Statistics offset (4 bytes)
            0,                                     # Indexes offset (4 bytes, not implemented)
            self.offsets.get("data_start", 0),    # Data offset (4 bytes)
            self.offsets.get("footer_start", 0),  # Footer offset (4 bytes)
            row_count,                             # Total row count (8 bytes)
            int(time.time()),                      # Created timestamp (8 bytes)
            int(time.time()),                      # Modified timestamp (8 bytes)
            self.compression_type,                 # Compression algorithm (1 byte)
            0,                                     # Encryption disabled (1 byte)
            # 14x = 14 bytes padding to reach 60 total
        )

        self.file_handle.write(header)

        # Restore position
        self.file_handle.seek(current_pos)

    def close(self):
        """Close the NCF file"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    import pandas as pd
    from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType, SemanticType

    print("NCF Writer - Basic Implementation")
    print("=" * 50)

    # Create sample data
    data = pd.DataFrame({
        "id": range(1000),
        "name": [f"User_{i}" for i in range(1000)],
        "age": np.random.randint(18, 80, 1000),
        "email": [f"user{i}@example.com" for i in range(1000)],
    })

    print(f"Sample data: {len(data)} rows, {len(data.columns)} columns")
    print(data.head())

    # Create schema
    schema = NCFSchema(
        table_name="users",
        columns=[
            ColumnSchema(
                name="id",
                data_type=NCFDataType.INT64,
                nullable=False,
                semantic_type=SemanticType.IDENTIFIER_KEY
            ),
            ColumnSchema(
                name="name",
                data_type=NCFDataType.STRING,
                semantic_type=SemanticType.PII_NAME,
                contains_pii=True
            ),
            ColumnSchema(
                name="age",
                data_type=NCFDataType.INT64,
                semantic_type=SemanticType.NUMERICAL
            ),
            ColumnSchema(
                name="email",
                data_type=NCFDataType.STRING,
                semantic_type=SemanticType.PII_EMAIL,
                contains_pii=True
            ),
        ]
    )

    # Write to NCF
    output_path = "test_output.ncf"
    print(f"\nWriting to {output_path}...")

    with NCFWriter(output_path, schema, compression="zstd") as writer:
        writer.write(data)

    print(f"✓ Successfully wrote {len(data)} rows to {output_path}")

    # Check file size
    import os
    file_size = os.path.getsize(output_path)
    print(f"✓ File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

    # Calculate compression ratio
    raw_size = data.memory_usage(deep=True).sum()
    compression_ratio = raw_size / file_size
    print(f"✓ Compression ratio: {compression_ratio:.2f}x")

    print("\nNCF Writer implementation complete!")
