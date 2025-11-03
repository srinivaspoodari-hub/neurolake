//! ZSTD compression with parallel support
//!
//! Uses zstd crate with multi-threading for column-parallel compression
//! Optimized for NCF's column-major layout

use std::io::{self, Write, Read};
use zstd::stream::{Encoder, Decoder};

/// Default compression level (1 = fast, 22 = best compression)
/// Level 1 provides best speed/compression tradeoff for NCF
pub const DEFAULT_COMPRESSION_LEVEL: i32 = 1;

/// Compress data using ZSTD
///
/// # Performance
/// - Level 1: ~500 MB/sec compression
/// - Level 3: ~300 MB/sec compression
/// - Level 10: ~50 MB/sec compression
///
/// For NCF, we use level 1 for maximum write speed
pub fn compress(data: &[u8], level: i32) -> io::Result<Vec<u8>> {
    let mut encoder = Encoder::new(Vec::new(), level)?;
    encoder.write_all(data)?;
    encoder.finish()
}

/// Decompress ZSTD data
pub fn decompress(compressed: &[u8]) -> io::Result<Vec<u8>> {
    let mut decoder = Decoder::new(compressed)?;
    let mut decompressed = Vec::new();
    decoder.read_to_end(&mut decompressed)?;
    Ok(decompressed)
}

/// Compress with default level (1)
#[inline]
pub fn compress_fast(data: &[u8]) -> io::Result<Vec<u8>> {
    compress(data, DEFAULT_COMPRESSION_LEVEL)
}

/// Parallel compression of multiple columns
///
/// Uses rayon for parallel compression across columns
/// This is ideal for NCF's column-major format
#[cfg(feature = "parallel")]
pub fn compress_columns_parallel(columns: Vec<Vec<u8>>, level: i32) -> io::Result<Vec<Vec<u8>>> {
    use rayon::prelude::*;

    columns
        .par_iter()
        .map(|col| compress(col, level))
        .collect::<io::Result<Vec<_>>>()
}

/// Sequential compression of multiple columns (fallback)
pub fn compress_columns(columns: Vec<Vec<u8>>, level: i32) -> io::Result<Vec<Vec<u8>>> {
    columns
        .iter()
        .map(|col| compress(col, level))
        .collect()
}

/// Parallel decompression of multiple columns
#[cfg(feature = "parallel")]
pub fn decompress_columns_parallel(columns: Vec<Vec<u8>>) -> io::Result<Vec<Vec<u8>>> {
    use rayon::prelude::*;

    columns
        .par_iter()
        .map(|col| decompress(col))
        .collect::<io::Result<Vec<_>>>()
}

/// Sequential decompression of multiple columns (fallback)
pub fn decompress_columns(columns: Vec<Vec<u8>>) -> io::Result<Vec<Vec<u8>>> {
    columns
        .iter()
        .map(|col| decompress(col))
        .collect()
}

/// Get compression ratio for data
pub fn compression_ratio(original_size: usize, compressed_size: usize) -> f64 {
    original_size as f64 / compressed_size as f64
}

/// Estimate compressed size (conservative estimate: 50% of original)
pub fn estimate_compressed_size(original_size: usize) -> usize {
    original_size / 2
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compress_decompress_roundtrip() {
        let data = b"Hello, world! This is test data for compression.";

        let compressed = compress(data, 1).unwrap();
        let decompressed = decompress(&compressed).unwrap();

        assert_eq!(data, decompressed.as_slice());
    }

    #[test]
    fn test_compress_fast() {
        let data = b"Fast compression test data";

        let compressed = compress_fast(data).unwrap();
        let decompressed = decompress(&compressed).unwrap();

        assert_eq!(data, decompressed.as_slice());
    }

    #[test]
    fn test_compression_ratio() {
        // Highly compressible data (repeated pattern)
        let data: Vec<u8> = vec![65u8; 10000]; // 10K of 'A's

        let compressed = compress(&data, 1).unwrap();
        let ratio = compression_ratio(data.len(), compressed.len());

        // Should compress very well (>10x)
        assert!(ratio > 10.0);
        assert!(compressed.len() < 1000);
    }

    #[test]
    fn test_multiple_compression_levels() {
        let data = b"Test data for different compression levels".repeat(100);

        let level1 = compress(&data, 1).unwrap();
        let level3 = compress(&data, 3).unwrap();
        let level10 = compress(&data, 10).unwrap();

        // Higher levels should compress better (smaller size)
        assert!(level10.len() <= level3.len());
        assert!(level3.len() <= level1.len());

        // All should decompress correctly
        assert_eq!(data, decompress(&level1).unwrap());
        assert_eq!(data, decompress(&level3).unwrap());
        assert_eq!(data, decompress(&level10).unwrap());
    }

    #[test]
    fn test_compress_columns() {
        let columns = vec![
            vec![1u8, 2, 3, 4, 5],
            vec![10u8, 20, 30, 40, 50],
            vec![100u8; 1000], // Highly compressible
        ];

        let compressed = compress_columns(columns.clone(), 1).unwrap();

        assert_eq!(compressed.len(), 3);

        // Decompress and verify
        let decompressed = decompress_columns(compressed).unwrap();

        assert_eq!(columns, decompressed);
    }

    #[test]
    #[cfg(feature = "parallel")]
    fn test_compress_columns_parallel() {
        let columns = vec![
            vec![1u8; 10000],
            vec![2u8; 10000],
            vec![3u8; 10000],
            vec![4u8; 10000],
        ];

        let compressed = compress_columns_parallel(columns.clone(), 1).unwrap();

        assert_eq!(compressed.len(), 4);

        // Decompress and verify
        let decompressed = decompress_columns_parallel(compressed).unwrap();

        assert_eq!(columns, decompressed);
    }

    #[test]
    fn test_empty_data() {
        let data: Vec<u8> = vec![];

        let compressed = compress(&data, 1).unwrap();
        let decompressed = decompress(&compressed).unwrap();

        assert_eq!(data, decompressed);
    }

    #[test]
    fn test_large_data() {
        // 1MB of data
        let data: Vec<u8> = (0..1_000_000).map(|i| (i % 256) as u8).collect();

        let compressed = compress(&data, 1).unwrap();
        let decompressed = decompress(&compressed).unwrap();

        assert_eq!(data, decompressed);

        // Should achieve some compression
        let ratio = compression_ratio(data.len(), compressed.len());
        assert!(ratio > 1.5);
    }

    #[test]
    fn test_binary_data() {
        // Test with actual binary data (not just ASCII)
        let data: Vec<u8> = (0u16..256).map(|x| x as u8).cycle().take(10000).collect();

        let compressed = compress(&data, 3).unwrap();
        let decompressed = decompress(&compressed).unwrap();

        assert_eq!(data, decompressed);
    }
}
