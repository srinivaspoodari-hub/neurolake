//! NCF Schema definitions

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// NCF data types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[pyclass]
pub enum NCFDataType {
    Int8,
    Int16,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    Float32,
    Float64,
    String,
    Binary,
    Date,
    Timestamp,
}

#[pymethods]
impl NCFDataType {
    #[staticmethod]
    fn int64() -> Self {
        NCFDataType::Int64
    }

    #[staticmethod]
    fn float64() -> Self {
        NCFDataType::Float64
    }

    #[staticmethod]
    fn string() -> Self {
        NCFDataType::String
    }

    fn __repr__(&self) -> String {
        format!("{:?}", self)
    }
}

/// Semantic types for AI-native features
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[pyclass]
pub enum SemanticType {
    None,
    PiiName,
    PiiEmail,
    PiiPhone,
    PiiAddress,
    Geographic,
    Temporal,
    Categorical,
    Embedding,
}

/// Column schema definition
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct ColumnSchema {
    #[pyo3(get, set)]
    pub name: String,

    #[pyo3(get, set)]
    pub data_type: NCFDataType,

    #[pyo3(get, set)]
    pub semantic_type: Option<SemanticType>,

    #[pyo3(get, set)]
    pub nullable: bool,
}

#[pymethods]
impl ColumnSchema {
    #[new]
    #[pyo3(signature = (name, data_type, semantic_type=None, nullable=true))]
    pub fn new(
        name: String,
        data_type: NCFDataType,
        semantic_type: Option<SemanticType>,
        nullable: bool,
    ) -> Self {
        ColumnSchema {
            name,
            data_type,
            semantic_type,
            nullable,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "ColumnSchema(name='{}', data_type={:?}, nullable={})",
            self.name, self.data_type, self.nullable
        )
    }
}

/// NCF Schema
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct NCFSchema {
    #[pyo3(get, set)]
    pub table_name: String,

    #[pyo3(get, set)]
    pub columns: Vec<ColumnSchema>,

    #[pyo3(get, set)]
    pub row_count: u64,

    #[pyo3(get, set)]
    pub version: u32,
}

#[pymethods]
impl NCFSchema {
    #[new]
    #[pyo3(signature = (table_name, columns, row_count=0, version=1))]
    pub fn new(
        table_name: String,
        columns: Vec<ColumnSchema>,
        row_count: u64,
        version: u32,
    ) -> Self {
        NCFSchema {
            table_name,
            columns,
            row_count,
            version,
        }
    }

    fn column_names(&self) -> Vec<String> {
        self.columns.iter().map(|c| c.name.clone()).collect()
    }

    fn to_dict(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("table_name", &self.table_name)?;
            dict.set_item("row_count", self.row_count)?;
            dict.set_item("version", self.version)?;

            let columns: Vec<_> = self
                .columns
                .iter()
                .map(|c| {
                    let col_dict = pyo3::types::PyDict::new(py);
                    col_dict.set_item("name", &c.name).unwrap();
                    col_dict.set_item("data_type", format!("{:?}", c.data_type)).unwrap();
                    col_dict.set_item("nullable", c.nullable).unwrap();
                    col_dict.into()
                })
                .collect::<Vec<PyObject>>();

            dict.set_item("columns", columns)?;

            Ok(dict.into())
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "NCFSchema(table_name='{}', columns={}, rows={})",
            self.table_name,
            self.columns.len(),
            self.row_count
        )
    }
}

// Non-Python methods for internal Rust use
impl NCFSchema {
    /// Serialize schema to msgpack bytes
    pub fn to_msgpack(&self) -> Result<Vec<u8>, rmp_serde::encode::Error> {
        rmp_serde::to_vec(self)
    }

    /// Deserialize schema from msgpack bytes
    pub fn from_msgpack(bytes: &[u8]) -> Result<Self, rmp_serde::decode::Error> {
        rmp_serde::from_slice(bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_schema_creation() {
        let column = ColumnSchema {
            name: "test_col".to_string(),
            data_type: NCFDataType::Int64,
            semantic_type: None,
            nullable: true,
        };

        let schema = NCFSchema {
            table_name: "test_table".to_string(),
            columns: vec![column],
            row_count: 0,
            version: 1,
        };

        assert_eq!(schema.table_name, "test_table");
        assert_eq!(schema.columns.len(), 1);
        assert_eq!(schema.columns[0].name, "test_col");
    }

    #[test]
    fn test_column_names() {
        let schema = NCFSchema {
            table_name: "test".to_string(),
            columns: vec![
                ColumnSchema {
                    name: "col1".to_string(),
                    data_type: NCFDataType::Int64,
                    semantic_type: None,
                    nullable: true,
                },
                ColumnSchema {
                    name: "col2".to_string(),
                    data_type: NCFDataType::String,
                    semantic_type: None,
                    nullable: true,
                },
            ],
            row_count: 0,
            version: 1,
        };

        let names = schema.column_names();
        assert_eq!(names, vec!["col1", "col2"]);
    }
}
