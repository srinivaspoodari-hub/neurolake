//! NCF format implementation module

pub mod schema;
pub mod writer;
pub mod reader;
pub mod reader_fast;

// Re-exports
pub use schema::{NCFSchema, ColumnSchema, NCFDataType, SemanticType};
pub use writer::NCFWriter;
pub use reader::NCFReader;

// Constants
pub const NCF_MAGIC: &[u8] = b"NCF\x01";
pub const NCF_FOOTER_MAGIC: &[u8] = b"NCFE";
pub const NCF_VERSION: u32 = 1;

// Compression types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum CompressionType {
    None = 0,
    Zstd = 1,
    Lz4 = 2,
    Neural = 3,
}

impl CompressionType {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(CompressionType::None),
            1 => Some(CompressionType::Zstd),
            2 => Some(CompressionType::Lz4),
            3 => Some(CompressionType::Neural),
            _ => None,
        }
    }
}
