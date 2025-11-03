"""
Optimized NCF Writer (Phase 1 Python Optimizations)

This is an optimized version of the NCF writer implementing:
1. Faster string serialization (pre-calculated buffers)
2. Single-pass statistics generation
3. Lower compression level (1 instead of 3)
4. Cached schema lookups

Expected: 2-3x performance improvement over writer.py
"""

import struct
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import zstandard as zstd
import msgpack

from .schema import NCFSchema, ColumnSchema, NCFDataType, SemanticType

# NCF Magic Numbers
NCF_MAGIC = b"NCF\x01"
NCF_FOOTER_MAGIC = b"NCFE"
NCF_VERSION = 1

# Compression types
COMPRESSION_NONE = 0
COMPRESSION_ZSTD = 1
COMPRESSION_LZ4 = 2
COMPRESSION_NEURAL = 3


class NCFWriterOptimized:
    """
    Optimized NCF format writer with 2-3x performance improvement
    """

    def __init__(
        self,
        file_path: str,
        schema: NCFSchema,
        compression: str = "zstd",
        compression_level: int = 1,  # Changed from 3 to 1
    ):
        """
        Initialize NCF writer

        Args:
            file_path: Path to output NCF file
            schema: NCF schema definition
            compression: Compression algorithm ("zstd" or "none")
            compression_level: ZSTD compression level (1-22, default 1 for speed)
        """
        self.file_path = Path(file_path)
        self.schema = schema
        self.compression = compression
        self.compression_level = compression_level

        # File handle
        self.file_handle = None

        # Track file offsets
        self.offsets = {
            "header_start": 0,
            "schema_start": 0,
            "statistics_start": 0,
            "data_start": 0,
            "footer_start": 0,
        }

        # Statistics collected during serialization
        self.statistics = {}

        # Track whether data has been written
        self.data_written = False

        # Compression type mapping
        if compression == "zstd":
            self.compression_type = 1  # ZSTD
        elif compression == "none":
            self.compression_type = 0  # No compression
        else:
            raise ValueError(f"Unsupported compression: {compression}")

        # Pre-build dtype map (cache)
        self._dtype_map = {
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

        # Pre-build schema lookup (cache)
        self._schema_by_name = {col.name: col for col in schema.columns}

    def __enter__(self):
        """Context manager entry"""
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False

    def _open(self):
        """Open file and write initial structures"""
        self.file_handle = open(self.file_path, "w+b")  # Read+write for checksum calculation

        # Write magic number
        self.file_handle.write(NCF_MAGIC)

        # Write version
        self.file_handle.write(struct.pack("<I", NCF_VERSION))

        # Write placeholder header (will be updated later)
        self.offsets["header_start"] = self.file_handle.tell()
        self._write_placeholder_header()

        # Write schema
        self.offsets["schema_start"] = self.file_handle.tell()
        schema_dict = self.schema.to_dict()
        schema_bytes = msgpack.packb(schema_dict)
        self.file_handle.write(struct.pack("<I", len(schema_bytes)))
        self.file_handle.write(schema_bytes)

        # Statistics will be written after data
        self.offsets["statistics_start"] = self.file_handle.tell()

    def write(self, data: pd.DataFrame):
        """
        Write DataFrame to NCF format

        Args:
            data: pandas DataFrame to write
        """
        if self.data_written:
            raise RuntimeError("Data already written. NCF files are write-once.")

        # Validate schema matches data
        if list(data.columns) != self.schema.column_names():
            raise ValueError(
                f"DataFrame columns don't match schema. "
                f"Expected: {self.schema.column_names()}, Got: {list(data.columns)}"
            )

        row_count = len(data)

        # Convert DataFrame to dict of columns (for faster access)
        columns = {col: data[col].values for col in data.columns}

        # Write column data (generates statistics during serialization)
        self._write_column_data(columns)

        # Write statistics
        self._write_statistics()

        # Record footer position
        self.offsets["footer_start"] = self.file_handle.tell()

        # Update header with correct offsets (including footer offset)
        self._update_header(row_count)

        # Write footer with checksum (calculated from finalized header)
        self._write_footer()

        self.data_written = True

    def _write_placeholder_header(self):
        """Write placeholder header (will be updated with correct offsets later)"""
        # Write NCF header (60 bytes)
        header = struct.pack(
            "<QQQQQIIQ",
            0,  # schema_offset (placeholder)
            0,  # statistics_offset (placeholder)
            0,  # data_offset (placeholder)
            0,  # footer_offset (placeholder)
            0,  # row_count (placeholder)
            0,  # created_timestamp (placeholder)
            0,  # modified_timestamp (placeholder)
            0,  # compression_type (placeholder)
        )
        self.file_handle.write(header)

    def _update_header(self, row_count: int):
        """Update header with actual offsets"""
        # Seek to header position
        self.file_handle.seek(self.offsets["header_start"])

        # Write header
        current_time = int(time.time())
        header = struct.pack(
            "<QQQQQIIQ",
            self.offsets["schema_start"],
            self.offsets["statistics_start"],
            self.offsets["data_start"],
            self.offsets["footer_start"],
            row_count,
            current_time,
            current_time,
            self.compression_type,
        )
        self.file_handle.write(header)

    def _write_statistics(self):
        """Write statistics section"""
        # Seek to statistics position
        self.file_handle.seek(self.offsets["statistics_start"])

        # Serialize statistics as msgpack
        stats_bytes = msgpack.packb(self.statistics, use_bin_type=True)

        # Write statistics length + data
        self.file_handle.write(struct.pack("<I", len(stats_bytes)))
        self.file_handle.write(stats_bytes)

        # Record data start position
        self.offsets["data_start"] = self.file_handle.tell()

    def _write_column_data(self, columns: Dict[str, np.ndarray]):
        """Write column data as column groups"""
        # Currently writing all columns as one group
        # Future: implement column groups for locality
        self._write_column_group(columns)

    def _write_column_group(self, columns: Dict[str, np.ndarray]):
        """Write a group of columns"""
        # For each column
        for col_name, col_data in columns.items():
            col_schema = self._schema_by_name[col_name]  # Cached lookup

            # Serialize column with statistics (single pass!)
            serialized, col_stats = self._serialize_column_with_stats(
                col_data, col_schema
            )

            # Store statistics
            self.statistics[col_name] = col_stats

            # Compress if enabled
            if self.compression_type == 1:  # ZSTD
                compressor = zstd.ZstdCompressor(level=self.compression_level)
                compressed = compressor.compress(serialized)
            else:
                compressed = serialized

            # Write column
            # Format: [compression_type:byte] [data_len:uint32] [data_blob]
            self.file_handle.write(struct.pack("<B", self.compression_type))
            self.file_handle.write(struct.pack("<I", len(compressed)))
            self.file_handle.write(compressed)

    def _serialize_column_with_stats(
        self, col_data: np.ndarray, col_schema: ColumnSchema
    ) -> tuple[bytes, dict]:
        """
        Optimized: Serialize column data AND calculate statistics in one pass

        Returns:
            (serialized_bytes, statistics_dict)
        """
        stats = {
            "min_value": None,
            "max_value": None,
            "null_count": 0,
            "total_count": len(col_data),
            "distinct_count": None,  # Skip expensive unique() for now
        }

        # Numeric types
        if col_schema.data_type in self._dtype_map:
            # Calculate stats (fast numpy operations)
            null_mask = pd.isna(col_data)
            stats["null_count"] = int(null_mask.sum())

            if stats["null_count"] < len(col_data):  # Has non-null values
                valid_data = col_data[~null_mask]
                stats["min_value"] = float(valid_data.min())
                stats["max_value"] = float(valid_data.max())

            # Serialize (fast tobytes)
            target_dtype = self._dtype_map[col_schema.data_type]
            col_data_typed = col_data.astype(target_dtype)
            serialized = col_data_typed.tobytes()

            return serialized, stats

        # String types (OPTIMIZED VERSION)
        elif col_schema.data_type == NCFDataType.STRING:
            # Calculate stats
            null_mask = pd.isna(col_data)
            stats["null_count"] = int(null_mask.sum())
            # Skip min/max for strings (not meaningful)

            # OPTIMIZED string serialization
            serialized = self._serialize_strings_fast(col_data)

            return serialized, stats

        else:
            # Fallback: pickle
            import pickle

            serialized = pickle.dumps(col_data)
            return serialized, stats

    def _serialize_strings_fast(self, col_data: np.ndarray) -> bytes:
        """
        OPTIMIZED: Fast string serialization with pre-allocated buffer

        Old version: Python loop with repeated allocations (0.062s for 150K strings)
        New version: Pre-calculate sizes, single allocation (target: 0.030s)
        """
        # Step 1: Encode all strings to bytes (vectorized where possible)
        string_bytes = [
            str(x).encode("utf-8") if x is not None else b"" for x in col_data
        ]

        num_strings = len(string_bytes)

        # Step 2: Calculate lengths (fast list comprehension)
        lengths = [len(s) for s in string_bytes]

        # Step 3: Calculate offsets (use numpy cumsum for speed)
        offsets_array = np.zeros(num_strings + 1, dtype=np.uint32)
        offsets_array[1:] = np.cumsum(lengths, dtype=np.uint32)
        offsets = offsets_array.tolist()

        # Step 4: Pre-allocate buffer (single allocation!)
        header_size = 4  # num_strings
        offsets_size = len(offsets) * 4  # offsets array
        data_size = offsets[-1]  # total string bytes
        total_size = header_size + offsets_size + data_size

        buffer = bytearray(total_size)

        # Step 5: Pack header
        struct.pack_into("<I", buffer, 0, num_strings)

        # Step 6: Pack offsets (single operation)
        offset_format = f"<{len(offsets)}I"
        struct.pack_into(offset_format, buffer, 4, *offsets)

        # Step 7: Copy string data (minimize allocations)
        pos = 4 + offsets_size
        for s in string_bytes:
            if len(s) > 0:
                buffer[pos : pos + len(s)] = s
                pos += len(s)

        return bytes(buffer)

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
            ("statistics", self.offsets.get("statistics_start", 0)),
            ("data", self.offsets.get("data_start", 0)),
            ("footer", self.offsets.get("footer_start", 0)),
        ]

        # Serialize offset index
        offset_index_bytes = msgpack.packb(offset_entries, use_bin_type=True)
        self.file_handle.write(struct.pack("<I", len(offset_index_bytes)))
        self.file_handle.write(offset_index_bytes)

    def close(self):
        """Close the file handle"""
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
