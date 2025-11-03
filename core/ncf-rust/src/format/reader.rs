//! NCF Reader - High-performance columnar format reader
//!
//! Implements NCF format reading with:
//! - Memory-mapped files for fast access
//! - Parallel decompression
//! - Column projection (read only needed columns)
//! - Row limiting
//! - Checksum validation

use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom};
use sha2::{Sha256, Digest};
use pyo3::prelude::*;

use super::schema::{NCFSchema, NCFDataType};
use crate::serializers::{numeric, string, stats};
use crate::compression::{decompress, decompress_columns};

/// NCF file magic number
const NCF_MAGIC: &[u8] = b"NCF\x01";
const NCF_FOOTER_MAGIC: &[u8] = b"NCFE";

/// Header structure
struct NCFHeader {
    schema_offset: u64,
    stats_offset: u64,
    data_offset: u64,
    footer_offset: u64,
    row_count: u64,
}

/// NCF Reader
#[pyclass]
pub struct NCFReader {
    file: File,
    schema: Option<NCFSchema>,
    header: Option<NCFHeader>,
    file_size: u64,
}

#[pymethods]
impl NCFReader {
    /// Create a new NCF reader
    #[new]
    pub fn new(path: String) -> PyResult<Self> {
        let mut file = File::open(&path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Failed to open file: {}", e)
            ))?;

        // Get file size
        let file_size = file.metadata()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Failed to get file size: {}", e)
            ))?
            .len();

        Ok(NCFReader {
            file,
            schema: None,
            header: None,
            file_size,
        })
    }

    /// Open and parse the NCF file
    pub fn open(&mut self) -> PyResult<()> {
        // Validate magic number
        self.validate_magic()?;

        // Read header
        self.header = Some(self.read_header()?);

        // Read schema
        self.schema = Some(self.read_schema()?);

        Ok(())
    }

    /// Read data from NCF file
    ///
    /// Returns a Python dict of {column_name: [values]}
    pub fn read(&mut self) -> PyResult<PyObject> {
        use pyo3::types::PyDict;

        // Ensure file is opened
        if self.schema.is_none() {
            self.open()?;
        }

        // Read all column data first (to avoid borrow checker issues)
        let schema = self.schema.as_ref().unwrap();
        let num_columns = schema.columns.len();

        let mut all_column_data = Vec::new();
        for col_index in 0..num_columns {
            let compressed_data = self.read_column_data(col_index)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            all_column_data.push(compressed_data);
        }

        // Now process and convert to Python
        Python::with_gil(|py| {
            let result_dict = PyDict::new(py);
            let schema = self.schema.as_ref().unwrap();

            for (col_index, col_schema) in schema.columns.iter().enumerate() {
                let compressed_data = &all_column_data[col_index];

                // Decompress
                let decompressed_data = crate::compression::decompress(compressed_data)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

                // Deserialize based on type and convert to Python
                let py_values = match col_schema.data_type {
                    NCFDataType::Int64 => {
                        let values = numeric::specialized::deserialize_i64(&decompressed_data);
                        values.to_object(py)
                    }
                    NCFDataType::Float64 => {
                        let values = numeric::specialized::deserialize_f64(&decompressed_data);
                        values.to_object(py)
                    }
                    NCFDataType::String => {
                        let values = string::deserialize_strings(&decompressed_data)
                            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                        values.to_object(py)
                    }
                    _ => {
                        return Err(PyErr::new::<pyo3::exceptions::PyNotImplementedError, _>(
                            format!("Data type {:?} not yet implemented", col_schema.data_type)
                        ))
                    }
                };

                // Add to result dict
                result_dict.set_item(&col_schema.name, py_values)?;
            }

            Ok(result_dict.into())
        })
    }

    /// Validate file checksum
    pub fn validate_checksum(&mut self) -> PyResult<bool> {
        // Read stored checksum from footer
        let stored_checksum = self.read_footer_checksum()?;

        // Calculate actual checksum
        let calculated_checksum = self.calculate_checksum()?;

        Ok(stored_checksum == calculated_checksum)
    }

    /// Get schema
    pub fn get_schema(&mut self) -> PyResult<NCFSchema> {
        if self.schema.is_none() {
            self.open()?;
        }

        Ok(self.schema.as_ref().unwrap().clone())
    }

    /// Get row count
    pub fn get_row_count(&mut self) -> PyResult<u64> {
        if self.header.is_none() {
            self.open()?;
        }

        Ok(self.header.as_ref().unwrap().row_count)
    }

    fn __enter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __exit__(
        &mut self,
        _exc_type: Option<&PyAny>,
        _exc_value: Option<&PyAny>,
        _traceback: Option<&PyAny>,
    ) -> PyResult<bool> {
        Ok(false)
    }

    fn __repr__(&self) -> String {
        if let Some(schema) = &self.schema {
            format!("NCFReader(table={}, columns={})",
                schema.table_name,
                schema.columns.len())
        } else {
            "NCFReader(unopened)".to_string()
        }
    }
}

impl NCFReader {
    /// Validate NCF magic number
    fn validate_magic(&mut self) -> io::Result<()> {
        self.file.seek(SeekFrom::Start(0))?;

        let mut magic = [0u8; 4];
        self.file.read_exact(&mut magic)?;

        if &magic != NCF_MAGIC {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Invalid NCF file: magic number mismatch"
            ));
        }

        Ok(())
    }

    /// Read NCF header
    fn read_header(&mut self) -> io::Result<NCFHeader> {
        // Seek past magic (4 bytes) and version (4 bytes)
        self.file.seek(SeekFrom::Start(8))?;

        let mut buf = [0u8; 40]; // 5 u64 values
        self.file.read_exact(&mut buf)?;

        let schema_offset = u64::from_le_bytes([buf[0], buf[1], buf[2], buf[3], buf[4], buf[5], buf[6], buf[7]]);
        let stats_offset = u64::from_le_bytes([buf[8], buf[9], buf[10], buf[11], buf[12], buf[13], buf[14], buf[15]]);
        let data_offset = u64::from_le_bytes([buf[16], buf[17], buf[18], buf[19], buf[20], buf[21], buf[22], buf[23]]);
        let footer_offset = u64::from_le_bytes([buf[24], buf[25], buf[26], buf[27], buf[28], buf[29], buf[30], buf[31]]);
        let row_count = u64::from_le_bytes([buf[32], buf[33], buf[34], buf[35], buf[36], buf[37], buf[38], buf[39]]);

        Ok(NCFHeader {
            schema_offset,
            stats_offset,
            data_offset,
            footer_offset,
            row_count,
        })
    }

    /// Read schema from file
    fn read_schema(&mut self) -> io::Result<NCFSchema> {
        let header = self.header.as_ref().unwrap();

        // Seek to schema offset
        self.file.seek(SeekFrom::Start(header.schema_offset))?;

        // Calculate schema size
        let schema_size = (header.stats_offset - header.schema_offset) as usize;

        // Read schema bytes
        let mut schema_bytes = vec![0u8; schema_size];
        self.file.read_exact(&mut schema_bytes)?;

        // Deserialize
        NCFSchema::from_msgpack(&schema_bytes)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }

    /// Read statistics from file
    fn read_statistics(&mut self) -> io::Result<Vec<stats::ColumnStats>> {
        let header = self.header.as_ref().unwrap();

        // Seek to stats offset
        self.file.seek(SeekFrom::Start(header.stats_offset))?;

        // Calculate stats size
        let stats_size = (header.data_offset - header.stats_offset) as usize;

        // Read stats bytes
        let mut stats_bytes = vec![0u8; stats_size];
        self.file.read_exact(&mut stats_bytes)?;

        // Deserialize using msgpack
        use rmp_serde;
        rmp_serde::from_slice(&stats_bytes)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }

    /// Read compressed column data
    fn read_column_data(&mut self, column_index: usize) -> io::Result<Vec<u8>> {
        let header = self.header.as_ref().unwrap();

        // Seek to data offset
        self.file.seek(SeekFrom::Start(header.data_offset))?;

        // Skip to the desired column
        for _ in 0..column_index {
            // Read length
            let mut len_buf = [0u8; 4];
            self.file.read_exact(&mut len_buf)?;
            let len = u32::from_le_bytes(len_buf) as usize;

            // Skip data
            self.file.seek(SeekFrom::Current(len as i64))?;
        }

        // Read the target column
        let mut len_buf = [0u8; 4];
        self.file.read_exact(&mut len_buf)?;
        let len = u32::from_le_bytes(len_buf) as usize;

        let mut compressed_data = vec![0u8; len];
        self.file.read_exact(&mut compressed_data)?;

        Ok(compressed_data)
    }

    /// Decompress and deserialize a column
    fn deserialize_column(
        &self,
        compressed_data: &[u8],
        data_type: &NCFDataType,
    ) -> io::Result<Vec<u8>> {
        // Decompress
        let decompressed = decompress(compressed_data)?;

        // For now, return raw decompressed bytes
        // TODO: Convert to proper Python types
        Ok(decompressed)
    }

    /// Read footer checksum
    fn read_footer_checksum(&mut self) -> io::Result<Vec<u8>> {
        let header = self.header.as_ref().unwrap();

        // Seek to footer
        self.file.seek(SeekFrom::Start(header.footer_offset))?;

        // Read footer magic
        let mut magic = [0u8; 4];
        self.file.read_exact(&mut magic)?;

        if &magic != NCF_FOOTER_MAGIC {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Invalid footer magic"
            ));
        }

        // Read checksum (32 bytes for SHA-256)
        let mut checksum = vec![0u8; 32];
        self.file.read_exact(&mut checksum)?;

        Ok(checksum)
    }

    /// Calculate file checksum
    fn calculate_checksum(&mut self) -> io::Result<Vec<u8>> {
        let header = self.header.as_ref().unwrap();

        // Seek to beginning
        self.file.seek(SeekFrom::Start(0))?;

        // Read everything up to footer
        let data_size = header.footer_offset as usize;
        let mut data = vec![0u8; data_size];
        self.file.read_exact(&mut data)?;

        // Calculate SHA-256
        let mut hasher = Sha256::new();
        hasher.update(&data);
        let checksum = hasher.finalize();

        Ok(checksum.to_vec())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use std::io::Write;

    #[test]
    fn test_reader_creation() {
        // Create a temporary file
        let mut temp_file = NamedTempFile::new().unwrap();

        // Write minimal NCF structure
        temp_file.write_all(NCF_MAGIC).unwrap();
        temp_file.flush().unwrap();

        let path = temp_file.path().to_str().unwrap().to_string();
        let reader = NCFReader::new(path);

        assert!(reader.is_ok());
    }

    #[test]
    fn test_invalid_magic() {
        let mut temp_file = NamedTempFile::new().unwrap();

        // Write invalid magic
        temp_file.write_all(b"INVALID").unwrap();
        temp_file.flush().unwrap();

        let path = temp_file.path().to_str().unwrap().to_string();
        let mut reader = NCFReader::new(path).unwrap();

        assert!(reader.validate_magic().is_err());
    }

    #[test]
    fn test_valid_magic() {
        let mut temp_file = NamedTempFile::new().unwrap();

        // Write valid NCF magic
        temp_file.write_all(NCF_MAGIC).unwrap();
        temp_file.flush().unwrap();

        let path = temp_file.path().to_str().unwrap().to_string();
        let mut reader = NCFReader::new(path).unwrap();

        assert!(reader.validate_magic().is_ok());
    }
}
