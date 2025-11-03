//! Compression module with parallel ZSTD
//!
//! Provides high-performance compression for NCF format
//! - ZSTD compression with level 1 for speed
//! - Parallel compression across columns
//! - Optimized for column-major layout

pub mod zstd_compression;

// Re-export commonly used functions
pub use zstd_compression::{
    compress, decompress,
    compress_fast,
    compress_columns, decompress_columns,
    compression_ratio,
};

#[cfg(feature = "parallel")]
pub use zstd_compression::{
    compress_columns_parallel,
    decompress_columns_parallel,
};
