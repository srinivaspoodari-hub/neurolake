//! NCF Writer - High-performance columnar format writer
//!
//! Implements NCF format specification with:
//! - Column-major layout
//! - ZSTD compression (level 1)
//! - SHA-256 checksums
//! - Single-pass statistics

use std::fs::File;
use std::io::{self, Write, Seek, SeekFrom};
use std::path::Path;
use sha2::{Sha256, Digest};
use pyo3::prelude::*;

use super::schema::{NCFSchema, ColumnSchema, NCFDataType};
use crate::serializers::{numeric, string, stats};
use crate::compression::{compress_fast, compression_ratio};

/// NCF file magic number
const NCF_MAGIC: &[u8] = b"NCF\x01";
const NCF_FOOTER_MAGIC: &[u8] = b"NCFE";
const NCF_VERSION: u32 = 1;

/// Header size (fixed 64 bytes)
const HEADER_SIZE: usize = 64;

/// NCF Writer
#[pyclass]
pub struct NCFWriter {
    file: File,
    schema: NCFSchema,
    rows_written: u64,
    hasher: Sha256,
}

/// Column data and metadata
struct ColumnData {
    serialized: Vec<u8>,
    compressed: Vec<u8>,
    stats: stats::ColumnStats,
}

#[pymethods]
impl NCFWriter {
    /// Create a new NCF writer
    #[new]
    pub fn new(path: String, schema: NCFSchema) -> PyResult<Self> {
        let file = File::create(&path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Failed to create file: {}", e)
            ))?;

        Ok(NCFWriter {
            file,
            schema,
            rows_written: 0,
            hasher: Sha256::new(),
        })
    }

    /// Write data to NCF file
    ///
    /// Accepts column data as Python dict of {column_name: [values]}
    pub fn write(&mut self, py: Python, data: PyObject) -> PyResult<()> {
        use pyo3::types::PyDict;

        // Convert PyObject to dict
        let data_dict = data.downcast::<PyDict>(py)?;

        // Process each column according to schema
        let mut column_data_list: Vec<ColumnData> = Vec::new();

        for col_schema in &self.schema.columns {
            // Get column data from dict
            let col_data = data_dict.get_item(&col_schema.name)?
                .ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                        format!("Column '{}' not found in data", col_schema.name)
                    )
                })?;

            // Process column based on type
            let column_result = self.process_column(&col_schema, col_data)?;
            column_data_list.push(column_result);
        }

        // Get row count from first column
        if let Some(first_col) = column_data_list.first() {
            self.rows_written = first_col.stats.total_count;
        }

        // Write the file
        self.write_header_placeholder()?;

        let schema_offset = self.write_schema()?;
        let stats_offset = self.write_statistics(&column_data_list)?;
        let data_offset = self.write_data(&column_data_list)?;
        let footer_offset = self.write_footer()?;

        // Update header with actual offsets
        self.update_header(schema_offset, stats_offset, data_offset, footer_offset)?;

        // Finalize
        self.finalize()?;

        Ok(())
    }

    /// Close writer and finalize file
    pub fn close(&mut self) -> PyResult<()> {
        self.finalize()?;
        Ok(())
    }
}

impl NCFWriter {
    /// Write header placeholder
    fn write_header_placeholder(&mut self) -> io::Result<()> {
        // Write magic
        self.file.write_all(NCF_MAGIC)?;
        self.update_hash(NCF_MAGIC);

        // Write version
        let version_bytes = NCF_VERSION.to_le_bytes();
        self.file.write_all(&version_bytes)?;
        self.update_hash(&version_bytes);

        // Write placeholder for offsets (will update later)
        let placeholder = vec![0u8; HEADER_SIZE - 8]; // 8 bytes used for magic+version
        self.file.write_all(&placeholder)?;
        self.update_hash(&placeholder);

        Ok(())
    }

    /// Serialize and compress a single column
    fn process_column(&self, col_schema: &ColumnSchema, col_data: &PyAny) -> PyResult<ColumnData> {
        use pyo3::types::PyList;

        // Convert to appropriate type and process
        match col_schema.data_type {
            NCFDataType::Int64 => {
                // Extract i64 values from Python list
                let py_list = col_data.downcast::<PyList>()?;
                let rust_vec: Vec<i64> = py_list.iter()
                    .map(|item| item.extract::<i64>())
                    .collect::<Result<Vec<_>, _>>()?;

                self.process_i64_column(&rust_vec)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
            }
            NCFDataType::Float64 => {
                // Extract f64 values from Python list
                let py_list = col_data.downcast::<PyList>()?;
                let rust_vec: Vec<f64> = py_list.iter()
                    .map(|item| item.extract::<f64>())
                    .collect::<Result<Vec<_>, _>>()?;

                self.process_f64_column(&rust_vec)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
            }
            NCFDataType::String => {
                // Extract String values from Python list
                let py_list = col_data.downcast::<PyList>()?;
                let rust_vec: Vec<String> = py_list.iter()
                    .map(|item| item.extract::<String>())
                    .collect::<Result<Vec<_>, _>>()?;

                self.process_string_column(&rust_vec)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
            }
            _ => {
                Err(PyErr::new::<pyo3::exceptions::PyNotImplementedError, _>(
                    format!("Data type {:?} not yet implemented", col_schema.data_type)
                ))
            }
        }
    }

    /// Process i64 column
    fn process_i64_column(&self, data: &[i64]) -> io::Result<ColumnData> {
        // Serialize
        let serialized = numeric::specialized::serialize_i64(data);

        // Calculate statistics
        let stats = stats::calculate_i64_stats(data);

        // Compress
        let compressed = compress_fast(&serialized)?;

        Ok(ColumnData {
            serialized,
            compressed,
            stats,
        })
    }

    /// Process f64 column
    fn process_f64_column(&self, data: &[f64]) -> io::Result<ColumnData> {
        let serialized = numeric::specialized::serialize_f64(data);
        let stats = stats::calculate_f64_stats(data);
        let compressed = compress_fast(&serialized)?;

        Ok(ColumnData {
            serialized,
            compressed,
            stats,
        })
    }

    /// Process string column
    fn process_string_column(&self, data: &[String]) -> io::Result<ColumnData> {
        let serialized = string::serialize_strings_fast(data);
        let stats = stats::calculate_string_stats(data);
        let compressed = compress_fast(&serialized)?;

        Ok(ColumnData {
            serialized,
            compressed,
            stats,
        })
    }

    /// Write schema to file
    fn write_schema(&mut self) -> io::Result<u64> {
        let schema_bytes = self.schema.to_msgpack()
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;

        let pos = self.file.stream_position()?;
        self.file.write_all(&schema_bytes)?;
        self.update_hash(&schema_bytes);

        Ok(pos)
    }

    /// Write statistics to file
    fn write_statistics(&mut self, column_stats: &[ColumnData]) -> io::Result<u64> {
        use rmp_serde;

        // Collect all stats
        let stats: Vec<&stats::ColumnStats> = column_stats
            .iter()
            .map(|cd| &cd.stats)
            .collect();

        let stats_bytes = rmp_serde::to_vec(&stats)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;

        let pos = self.file.stream_position()?;
        self.file.write_all(&stats_bytes)?;
        self.update_hash(&stats_bytes);

        Ok(pos)
    }

    /// Write compressed column data to file
    fn write_data(&mut self, column_data: &[ColumnData]) -> io::Result<u64> {
        let pos = self.file.stream_position()?;

        for col in column_data {
            // Write compressed data length
            let len = col.compressed.len() as u32;
            let len_bytes = len.to_le_bytes();
            self.file.write_all(&len_bytes)?;
            self.update_hash(&len_bytes);

            // Write compressed data
            self.file.write_all(&col.compressed)?;
            self.update_hash(&col.compressed);
        }

        Ok(pos)
    }

    /// Write footer with checksum
    fn write_footer(&mut self) -> io::Result<u64> {
        let pos = self.file.stream_position()?;

        // Write footer magic
        self.file.write_all(NCF_FOOTER_MAGIC)?;

        // Calculate and write checksum (not included in hash)
        let checksum = self.hasher.finalize_reset();
        self.file.write_all(&checksum)?;

        Ok(pos)
    }

    /// Update running hash
    fn update_hash(&mut self, data: &[u8]) {
        self.hasher.update(data);
    }

    /// Update header with actual offsets
    fn update_header(
        &mut self,
        schema_offset: u64,
        stats_offset: u64,
        data_offset: u64,
        footer_offset: u64,
    ) -> io::Result<()> {
        // Seek to header position (after magic and version)
        self.file.seek(SeekFrom::Start(8))?;

        // Write offsets
        self.file.write_all(&schema_offset.to_le_bytes())?;
        self.file.write_all(&stats_offset.to_le_bytes())?;
        self.file.write_all(&data_offset.to_le_bytes())?;
        self.file.write_all(&footer_offset.to_le_bytes())?;
        self.file.write_all(&self.rows_written.to_le_bytes())?;

        Ok(())
    }

    /// Finalize file and write all metadata
    fn finalize(&mut self) -> io::Result<()> {
        // For now, just flush
        self.file.flush()?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[test]
    fn test_writer_creation() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path().to_str().unwrap().to_string();

        let schema = NCFSchema::new(
            "test_table".to_string(),
            vec![
                ColumnSchema::new("id".to_string(), NCFDataType::Int64, None, true),
                ColumnSchema::new("value".to_string(), NCFDataType::Float64, None, true),
            ],
            0,
            1,
        );

        let writer = NCFWriter::new(path, schema);
        assert!(writer.is_ok());
    }

    #[test]
    fn test_process_i64_column() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path().to_str().unwrap().to_string();

        let schema = NCFSchema::new(
            "test".to_string(),
            vec![ColumnSchema::new("id".to_string(), NCFDataType::Int64, None, true)],
            0,
            1,
        );

        let writer = NCFWriter::new(path, schema).unwrap();

        let data = vec![1i64, 2, 3, 4, 5];
        let result = writer.process_i64_column(&data).unwrap();

        // Verify statistics
        assert_eq!(result.stats.min_value, Some(1.0));
        assert_eq!(result.stats.max_value, Some(5.0));
        assert_eq!(result.stats.total_count, 5);

        // Verify compression
        assert!(result.compressed.len() < result.serialized.len());
    }

    #[test]
    fn test_process_string_column() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path().to_str().unwrap().to_string();

        let schema = NCFSchema::new(
            "test".to_string(),
            vec![ColumnSchema::new("name".to_string(), NCFDataType::String, None, true)],
            0,
            1,
        );

        let writer = NCFWriter::new(path, schema).unwrap();

        let data = vec![
            "hello".to_string(),
            "world".to_string(),
            "test".to_string(),
        ];
        let result = writer.process_string_column(&data).unwrap();

        // Verify statistics
        assert_eq!(result.stats.total_count, 3);
        assert_eq!(result.stats.null_count, 0);
    }

    #[test]
    fn test_compression_effectiveness() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path().to_str().unwrap().to_string();

        let schema = NCFSchema::new(
            "test".to_string(),
            vec![ColumnSchema::new("id".to_string(), NCFDataType::Int64, None, true)],
            0,
            1,
        );

        let writer = NCFWriter::new(path, schema).unwrap();

        // Highly compressible data
        let data = vec![42i64; 1000];
        let result = writer.process_i64_column(&data).unwrap();

        let ratio = compression_ratio(result.serialized.len(), result.compressed.len());

        // Should achieve good compression on repeated data
        assert!(ratio > 5.0);
    }
}
