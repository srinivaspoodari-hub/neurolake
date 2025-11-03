"""
NCF Writer with Cython Acceleration (Phase 2)

This writer uses Cython-optimized serializers for maximum performance.

Expected: 3-5x speedup over original, 1.5-2x over Phase 1
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

# Try to import Cython serializers
try:
    from . import serializers as cython_serializers
    HAS_CYTHON = True
except ImportError:
    HAS_CYTHON = False
    print("Warning: Cython serializers not available. Please build with: python setup_cython.py build_ext --inplace")

# NCF Magic Numbers
NCF_MAGIC = b"NCF\x01"
NCF_FOOTER_MAGIC = b"NCFE"
NCF_VERSION = 1

# Compression types
COMPRESSION_NONE = 0
COMPRESSION_ZSTD = 1
COMPRESSION_LZ4 = 2
COMPRESSION_NEURAL = 3


class NCFWriterCython:
    """
    Cython-accelerated NCF format writer

    This is the fastest Python-based NCF writer, using Cython for hot paths.
    Expected to be 3-5x faster than original, 1.5-2x faster than Phase 1.
    """

    def __init__(
        self,
        file_path: str,
        schema: NCFSchema,
        compression: str = "zstd",
        compression_level: int = 1,
    ):
        """
        Initialize Cython-accelerated NCF writer

        Args:
            file_path: Path to output NCF file
            schema: NCF schema definition
            compression: Compression algorithm ("zstd" or "none")
            compression_level: ZSTD compression level (1-22, default 1 for speed)
        """
        if not HAS_CYTHON:
            raise RuntimeError(
                "Cython serializers not available. "
                "Build with: python setup_cython.py build_ext --inplace"
            )

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
        self.file_handle = open(self.file_path, "w+b")

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
        Write DataFrame to NCF format using Cython acceleration

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
        self.file_handle.seek(self.offsets["header_start"])

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
        self.file_handle.seek(self.offsets["statistics_start"])

        stats_bytes = msgpack.packb(self.statistics, use_bin_type=True)
        self.file_handle.write(struct.pack("<I", len(stats_bytes)))
        self.file_handle.write(stats_bytes)

        self.offsets["data_start"] = self.file_handle.tell()

    def _write_column_data(self, columns: Dict[str, np.ndarray]):
        """Write column data using Cython serializers"""
        for col_name, col_data in columns.items():
            col_schema = self._schema_by_name[col_name]

            # Serialize column with statistics (Cython-accelerated!)
            serialized, col_stats = self._serialize_column_with_stats_cython(
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
            self.file_handle.write(struct.pack("<B", self.compression_type))
            self.file_handle.write(struct.pack("<I", len(compressed)))
            self.file_handle.write(compressed)

    def _serialize_column_with_stats_cython(
        self, col_data: np.ndarray, col_schema: ColumnSchema
    ) -> tuple:
        """
        CYTHON-ACCELERATED: Serialize column data AND calculate statistics

        Uses Cython functions for maximum performance

        Returns:
            (serialized_bytes, statistics_dict)
        """
        # Numeric types (Cython-accelerated)
        if col_schema.data_type in self._dtype_map:
            target_dtype = self._dtype_map[col_schema.data_type]

            # Use Cython serializer
            serialized = cython_serializers.serialize_numeric_fast(
                col_data, target_dtype
            )

            # Use Cython stats calculator
            stats = cython_serializers.calculate_numeric_stats_fast(col_data)

            return serialized, stats

        # String types (Cython-accelerated)
        elif col_schema.data_type == NCFDataType.STRING:
            # Use Cython string serializer (2-3x faster!)
            serialized = cython_serializers.serialize_strings_fast(col_data)

            # Calculate basic stats
            null_mask = pd.isna(col_data)
            stats = {
                "min_value": None,
                "max_value": None,
                "null_count": int(null_mask.sum()),
                "total_count": len(col_data),
                "distinct_count": None,
            }

            return serialized, stats

        else:
            # Fallback: pickle
            import pickle

            serialized = pickle.dumps(col_data)
            stats = {
                "min_value": None,
                "max_value": None,
                "null_count": 0,
                "total_count": len(col_data),
                "distinct_count": None,
            }
            return serialized, stats

    def _write_footer(self):
        """Write footer with checksum"""
        self.file_handle.seek(self.offsets["footer_start"])

        # Calculate checksum
        self.file_handle.flush()
        self.file_handle.seek(0)
        hasher = hashlib.sha256()

        bytes_to_hash = self.offsets["footer_start"]
        chunk_size = 1024 * 1024

        bytes_read = 0
        while bytes_read < bytes_to_hash:
            to_read = min(chunk_size, bytes_to_hash - bytes_read)
            chunk = self.file_handle.read(to_read)
            if not chunk:
                break
            hasher.update(chunk)
            bytes_read += len(chunk)

        checksum = hasher.digest()

        # Write footer
        self.file_handle.seek(self.offsets["footer_start"])
        self.file_handle.write(NCF_FOOTER_MAGIC)
        self.file_handle.write(struct.pack("<I", 1))
        self.file_handle.write(struct.pack("<B", 2))
        self.file_handle.write(checksum)

        # Write offset index
        offset_entries = [
            ("header", self.offsets.get("header_start", 0)),
            ("schema", self.offsets.get("schema_start", 0)),
            ("statistics", self.offsets.get("statistics_start", 0)),
            ("data", self.offsets.get("data_start", 0)),
            ("footer", self.offsets.get("footer_start", 0)),
        ]

        offset_index_bytes = msgpack.packb(offset_entries, use_bin_type=True)
        self.file_handle.write(struct.pack("<I", len(offset_index_bytes)))
        self.file_handle.write(offset_index_bytes)

    def close(self):
        """Close the file handle"""
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
