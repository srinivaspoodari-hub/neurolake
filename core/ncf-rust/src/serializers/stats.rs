//! Fast statistics calculation for columns
//!
//! Single-pass calculation of min/max/null_count
//! Optimized with potential SIMD acceleration

use serde::{Deserialize, Serialize};

/// Column statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnStats {
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
    pub null_count: u64,
    pub total_count: u64,
    pub distinct_count: Option<u64>,  // Expensive, usually None
}

/// Calculate statistics for integer array
pub fn calculate_i64_stats(data: &[i64]) -> ColumnStats {
    if data.is_empty() {
        return ColumnStats {
            min_value: None,
            max_value: None,
            null_count: 0,
            total_count: 0,
            distinct_count: None,
        };
    }

    let mut min = data[0];
    let mut max = data[0];

    // Unrolled loop for better performance
    let chunks = data.chunks_exact(4);
    let remainder = chunks.remainder();

    for chunk in chunks {
        min = min.min(chunk[0]).min(chunk[1]).min(chunk[2]).min(chunk[3]);
        max = max.max(chunk[0]).max(chunk[1]).max(chunk[2]).max(chunk[3]);
    }

    for &val in remainder {
        min = min.min(val);
        max = max.max(val);
    }

    ColumnStats {
        min_value: Some(min as f64),
        max_value: Some(max as f64),
        null_count: 0,  // No NULLs in non-nullable arrays
        total_count: data.len() as u64,
        distinct_count: None,
    }
}

/// Calculate statistics for float array
pub fn calculate_f64_stats(data: &[f64]) -> ColumnStats {
    if data.is_empty() {
        return ColumnStats {
            min_value: None,
            max_value: None,
            null_count: 0,
            total_count: 0,
            distinct_count: None,
        };
    }

    let mut min = f64::INFINITY;
    let mut max = f64::NEG_INFINITY;
    let mut null_count = 0u64;
    let mut has_values = false;

    // Handle NaN values (they represent NULL in floats)
    for &val in data {
        if val.is_nan() {
            null_count += 1;
        } else {
            has_values = true;
            if val < min {
                min = val;
            }
            if val > max {
                max = val;
            }
        }
    }

    ColumnStats {
        min_value: if has_values { Some(min) } else { None },
        max_value: if has_values { Some(max) } else { None },
        null_count,
        total_count: data.len() as u64,
        distinct_count: None,
    }
}

/// Calculate statistics for string array
pub fn calculate_string_stats(data: &[String]) -> ColumnStats {
    let mut null_count = 0u64;

    for s in data {
        if s.is_empty() {
            null_count += 1;
        }
    }

    ColumnStats {
        min_value: None,  // Min/max not meaningful for strings
        max_value: None,
        null_count,
        total_count: data.len() as u64,
        distinct_count: None,  // Would need HashSet, skip for performance
    }
}

// TODO: SIMD-optimized versions
#[cfg(target_arch = "x86_64")]
pub mod simd {
    use super::*;

    // TODO: Implement AVX2/AVX512 versions
    // pub fn calculate_f64_stats_avx2(data: &[f64]) -> ColumnStats { ... }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_i64_stats() {
        let data = vec![1i64, 5, 3, 9, 2, 7];
        let stats = calculate_i64_stats(&data);

        assert_eq!(stats.min_value, Some(1.0));
        assert_eq!(stats.max_value, Some(9.0));
        assert_eq!(stats.null_count, 0);
        assert_eq!(stats.total_count, 6);
    }

    #[test]
    fn test_f64_stats_with_nan() {
        let data = vec![1.5, f64::NAN, 3.7, 2.1, f64::NAN];
        let stats = calculate_f64_stats(&data);

        assert_eq!(stats.min_value, Some(1.5));
        assert_eq!(stats.max_value, Some(3.7));
        assert_eq!(stats.null_count, 2);
        assert_eq!(stats.total_count, 5);
    }

    #[test]
    fn test_empty_array() {
        let data: Vec<i64> = vec![];
        let stats = calculate_i64_stats(&data);

        assert_eq!(stats.min_value, None);
        assert_eq!(stats.max_value, None);
        assert_eq!(stats.total_count, 0);
    }

    #[test]
    fn test_large_array() {
        let data: Vec<i64> = (0..100_000).collect();
        let stats = calculate_i64_stats(&data);

        assert_eq!(stats.min_value, Some(0.0));
        assert_eq!(stats.max_value, Some(99_999.0));
        assert_eq!(stats.total_count, 100_000);
    }
}
