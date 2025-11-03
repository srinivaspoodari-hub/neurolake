"""
Integration tests for NCF Rust implementation (v2.0)

Tests the complete Rust NCF writer/reader pipeline with Python integration.
Requires: Rust implementation built with maturin

To run:
    1. Install Rust: winget install Rustlang.Rustup
    2. Build module: cd core/ncf-rust && maturin develop --release
    3. Run tests: pytest tests/test_rust_integration.py -v
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os

# Try to import Rust implementation
try:
    from ncf_rust import NCFWriter as NCFWriterRust, NCFReader as NCFReaderRust, NCFSchema as NCFSchemaRust
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Rust NCF module not built. Run: cd core/ncf-rust && maturin develop --release")

# Import Python implementation for comparison
from neurolake.ncf.format.writer_optimized import NCFWriterOptimized
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType


class TestRustIntegration:
    """Integration tests for Rust NCF implementation"""

    def create_test_schema(self):
        """Create a test schema"""
        return NCFSchema(
            table_name="test_table",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="name", data_type=NCFDataType.STRING),
            ]
        )

    def create_test_data(self, num_rows=1000):
        """Create test DataFrame"""
        return pd.DataFrame({
            'id': np.arange(num_rows, dtype=np.int64),
            'value': np.random.randn(num_rows),
            'name': [f"Name_{i}" for i in range(num_rows)],
        })

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_write_read_roundtrip(self):
        """Test basic write/read roundtrip with Rust implementation"""
        schema = self.create_test_schema()
        data = self.create_test_data(100)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write with Rust
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)

            # Read with Rust
            with NCFReaderRust(tmp_path) as reader:
                result = reader.read()

            # Verify
            assert result is not None
            # TODO: Add more assertions once DataFrame conversion is implemented

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_checksum_validation(self):
        """Test checksum validation in Rust reader"""
        schema = self.create_test_schema()
        data = self.create_test_data(100)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write with Python (known good)
            with NCFWriterOptimized(tmp_path, schema) as writer:
                writer.write(data)

            # Read with Rust and validate checksum
            with NCFReaderRust(tmp_path) as reader:
                assert reader.validate_checksum() == True

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_python_interop_write(self):
        """Test Rust writer, Python reader interoperability"""
        schema = self.create_test_schema()
        data = self.create_test_data(100)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write with Rust
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)

            # Read with Python
            with NCFReader(tmp_path) as reader:
                assert reader.validate_checksum()
                result = reader.read()

            # Verify data matches
            pd.testing.assert_frame_equal(result, data)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_python_rust_interop_read(self):
        """Test Python writer, Rust reader interoperability"""
        schema = self.create_test_schema()
        data = self.create_test_data(100)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write with Python
            with NCFWriterOptimized(tmp_path, schema) as writer:
                writer.write(data)

            # Read with Rust
            with NCFReaderRust(tmp_path) as reader:
                assert reader.validate_checksum()
                result = reader.read()

            # TODO: Verify data matches once DataFrame conversion is implemented

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_column_projection(self):
        """Test reading specific columns only"""
        schema = self.create_test_schema()
        data = self.create_test_data(100)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write all columns
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)

            # Read only specific columns
            with NCFReaderRust(tmp_path) as reader:
                result = reader.read(columns=['id', 'name'])

            # Verify only requested columns present
            # TODO: Implement once read() returns DataFrame

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_row_limiting(self):
        """Test reading limited number of rows"""
        schema = self.create_test_schema()
        data = self.create_test_data(1000)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write 1000 rows
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)

            # Read only 100 rows
            with NCFReaderRust(tmp_path) as reader:
                result = reader.read(limit=100)

            # Verify row count
            # TODO: Implement once read() returns DataFrame

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_large_dataset(self):
        """Test with large dataset (100K rows)"""
        schema = self.create_test_schema()
        data = self.create_test_data(100000)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)

            # Read
            with NCFReaderRust(tmp_path) as reader:
                assert reader.validate_checksum()
                assert reader.get_row_count() == 100000
                result = reader.read()

            # Verify
            # TODO: Implement once read() returns DataFrame

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_schema_access(self):
        """Test schema access from Rust reader"""
        schema = self.create_test_schema()
        data = self.create_test_data(100)

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            with NCFWriterOptimized(tmp_path, schema) as writer:
                writer.write(data)

            # Read schema
            with NCFReaderRust(tmp_path) as reader:
                read_schema = reader.get_schema()

            # Verify schema
            assert read_schema.table_name == schema.table_name
            assert len(read_schema.columns) == len(schema.columns)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_unicode_strings(self):
        """Test handling of Unicode strings"""
        schema = NCFSchema(
            table_name="unicode_test",
            columns=[
                ColumnSchema(name="text", data_type=NCFDataType.STRING),
            ]
        )

        data = pd.DataFrame({
            'text': [
                "Hello 世界",
                "Rust 🦀",
                "عربي",
                "Русский",
                "Emoji: 🚀💡🎉",
            ]
        })

        with tempfile.NamedTemporaryFile(suffix='.ncf', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write
            with NCFWriterRust(tmp_path, schema) as writer:
                writer.write(data)

            # Read
            with NCFReaderRust(tmp_path) as reader:
                result = reader.read()

            # Verify
            # TODO: Implement once read() returns DataFrame

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestRustPythonComparison:
    """Compare Rust and Python implementations"""

    def create_benchmark_data(self, num_rows=10000):
        """Create benchmark dataset"""
        return pd.DataFrame({
            'id': np.arange(num_rows, dtype=np.int64),
            'value1': np.random.randn(num_rows),
            'value2': np.random.randn(num_rows),
            'category': np.random.choice(['A', 'B', 'C'], num_rows),
            'text': [f"Text_{i}" for i in range(num_rows)],
        })

    def create_benchmark_schema(self):
        """Create schema for benchmark"""
        return NCFSchema(
            table_name="benchmark",
            columns=[
                ColumnSchema(name="id", data_type=NCFDataType.INT64),
                ColumnSchema(name="value1", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="value2", data_type=NCFDataType.FLOAT64),
                ColumnSchema(name="category", data_type=NCFDataType.STRING),
                ColumnSchema(name="text", data_type=NCFDataType.STRING),
            ]
        )

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_vs_python_file_size(self):
        """Compare file sizes between Rust and Python implementations"""
        schema = self.create_benchmark_schema()
        data = self.create_benchmark_data(10000)

        with tempfile.NamedTemporaryFile(suffix='_rust.ncf', delete=False) as tmp_rust:
            rust_path = tmp_rust.name

        with tempfile.NamedTemporaryFile(suffix='_python.ncf', delete=False) as tmp_python:
            python_path = tmp_python.name

        try:
            # Write with Rust
            with NCFWriterRust(rust_path, schema) as writer:
                writer.write(data)

            # Write with Python
            with NCFWriterOptimized(python_path, schema) as writer:
                writer.write(data)

            # Compare sizes
            rust_size = os.path.getsize(rust_path)
            python_size = os.path.getsize(python_path)

            print(f"\nRust file size: {rust_size:,} bytes")
            print(f"Python file size: {python_size:,} bytes")
            print(f"Difference: {abs(rust_size - python_size):,} bytes")

            # Files should be similar size (within 5%)
            assert abs(rust_size - python_size) / python_size < 0.05

        finally:
            for path in [rust_path, python_path]:
                if os.path.exists(path):
                    os.remove(path)

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
    def test_rust_vs_python_correctness(self):
        """Verify Rust and Python produce identical results"""
        schema = self.create_benchmark_schema()
        data = self.create_benchmark_data(1000)

        with tempfile.NamedTemporaryFile(suffix='_rust.ncf', delete=False) as tmp_rust:
            rust_path = tmp_rust.name

        with tempfile.NamedTemporaryFile(suffix='_python.ncf', delete=False) as tmp_python:
            python_path = tmp_python.name

        try:
            # Write with Rust
            with NCFWriterRust(rust_path, schema) as writer:
                writer.write(data)

            # Write with Python
            with NCFWriterOptimized(python_path, schema) as writer:
                writer.write(data)

            # Read both
            with NCFReader(rust_path) as reader:
                rust_data = reader.read()

            with NCFReader(python_path) as reader:
                python_data = reader.read()

            # Compare
            pd.testing.assert_frame_equal(rust_data, python_data)

        finally:
            for path in [rust_path, python_path]:
                if os.path.exists(path):
                    os.remove(path)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
