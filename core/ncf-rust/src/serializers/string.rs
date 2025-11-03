//! High-performance string serialization
//!
//! Format: [count:u32][offsets:u32[]...[data_blob]
//!
//! This is optimized for:
//! - Single memory allocation
//! - Minimal copies
//! - Fast encoding/decoding

use byteorder::{LittleEndian, WriteBytesExt, ReadBytesExt};
use std::io::{Cursor, Write};

/// Serialize string array to bytes
///
/// # Performance
/// - Single allocation
/// - Pre-calculated sizes
/// - Minimal copies
/// - Expected: 2-3x faster than Python
pub fn serialize_strings(strings: &[String]) -> Result<Vec<u8>, std::io::Error> {
    let num_strings = strings.len();

    // Pre-calculate total size
    let mut total_data_size = 0usize;
    for s in strings {
        total_data_size += s.len();
    }

    // Calculate buffer size
    // 4 bytes for count + (num_strings + 1) * 4 for offsets + data
    let buffer_size = 4 + (num_strings + 1) * 4 + total_data_size;

    // Single allocation
    let mut buffer = Vec::with_capacity(buffer_size);
    let mut cursor = Cursor::new(&mut buffer);

    // Write count
    cursor.write_u32::<LittleEndian>(num_strings as u32)?;

    // Calculate and write offsets
    let mut offset = 0u32;
    cursor.write_u32::<LittleEndian>(offset)?; // First offset is 0

    for s in strings {
        offset += s.len() as u32;
        cursor.write_u32::<LittleEndian>(offset)?;
    }

    // Write string data
    for s in strings {
        cursor.write_all(s.as_bytes())?;
    }

    Ok(buffer)
}

/// Deserialize string array from bytes
pub fn deserialize_strings(data: &[u8]) -> Result<Vec<String>, std::io::Error> {
    let mut cursor = Cursor::new(data);

    // Read count
    let num_strings = cursor.read_u32::<LittleEndian>()? as usize;

    // Read offsets
    let mut offsets = Vec::with_capacity(num_strings + 1);
    for _ in 0..=num_strings {
        offsets.push(cursor.read_u32::<LittleEndian>()? as usize);
    }

    // Calculate data start position
    let data_start = 4 + (num_strings + 1) * 4;

    // Extract strings
    let mut strings = Vec::with_capacity(num_strings);
    for i in 0..num_strings {
        let start = data_start + offsets[i];
        let end = data_start + offsets[i + 1];
        let string_bytes = &data[start..end];
        let s = String::from_utf8_lossy(string_bytes).to_string();
        strings.push(s);
    }

    Ok(strings)
}

/// Optimized version using pre-allocated buffer
pub fn serialize_strings_fast(strings: &[String]) -> Vec<u8> {
    let num_strings = strings.len();

    // Pre-calculate exact size
    let mut data_size = 0;
    for s in strings {
        data_size += s.len();
    }

    let total_size = 4 + (num_strings + 1) * 4 + data_size;

    // Single allocation
    let mut buffer = vec![0u8; total_size];

    // Write count
    let count_bytes = (num_strings as u32).to_le_bytes();
    buffer[0..4].copy_from_slice(&count_bytes);

    // Write offsets and data
    let offset_start = 4;
    let data_start = offset_start + (num_strings + 1) * 4;

    let mut current_offset = 0u32;
    buffer[offset_start..offset_start + 4].copy_from_slice(&current_offset.to_le_bytes());

    let mut data_pos = data_start;
    for (i, s) in strings.iter().enumerate() {
        // Write string data
        let s_bytes = s.as_bytes();
        buffer[data_pos..data_pos + s_bytes.len()].copy_from_slice(s_bytes);
        data_pos += s_bytes.len();

        // Write next offset
        current_offset += s_bytes.len() as u32;
        let offset_pos = offset_start + (i + 1) * 4;
        buffer[offset_pos..offset_pos + 4].copy_from_slice(&current_offset.to_le_bytes());
    }

    buffer
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_roundtrip() {
        let strings = vec![
            "hello".to_string(),
            "world".to_string(),
            "test".to_string(),
            "".to_string(),  // Empty string
            "🚀".to_string(),  // Unicode
        ];

        let serialized = serialize_strings(&strings).unwrap();
        let deserialized = deserialize_strings(&serialized).unwrap();

        assert_eq!(strings, deserialized);
    }

    #[test]
    fn test_string_fast_roundtrip() {
        let strings = vec![
            "fast".to_string(),
            "serialization".to_string(),
            "test".to_string(),
        ];

        let serialized = serialize_strings_fast(&strings);
        let deserialized = deserialize_strings(&serialized).unwrap();

        assert_eq!(strings, deserialized);
    }

    #[test]
    fn test_large_strings() {
        let strings: Vec<String> = (0..10_000)
            .map(|i| format!("String number {}", i))
            .collect();

        let serialized = serialize_strings_fast(&strings);
        let deserialized = deserialize_strings(&serialized).unwrap();

        assert_eq!(strings.len(), deserialized.len());
        assert_eq!(strings[0], deserialized[0]);
        assert_eq!(strings[9999], deserialized[9999]);
    }

    #[test]
    fn test_unicode_strings() {
        let strings = vec![
            "Hello 世界".to_string(),
            "Rust 🦀".to_string(),
            "عربي".to_string(),
            "Русский".to_string(),
        ];

        let serialized = serialize_strings_fast(&strings);
        let deserialized = deserialize_strings(&serialized).unwrap();

        assert_eq!(strings, deserialized);
    }
}
