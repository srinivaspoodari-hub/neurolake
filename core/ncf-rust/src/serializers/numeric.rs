//! High-performance numeric serialization with zero-copy operations

use std::mem;

/// Serialize numeric data to bytes (zero-copy where possible)
pub fn serialize_numeric<T: Copy>(data: &[T]) -> Vec<u8> {
    // Calculate size
    let size = data.len() * mem::size_of::<T>();

    // Allocate buffer
    let mut buffer = Vec::with_capacity(size);

    // SAFETY: We're copying POD types (Plain Old Data)
    unsafe {
        let src_ptr = data.as_ptr() as *const u8;
        let dst_ptr = buffer.as_mut_ptr();
        std::ptr::copy_nonoverlapping(src_ptr, dst_ptr, size);
        buffer.set_len(size);
    }

    buffer
}

/// Deserialize numeric data from bytes
pub fn deserialize_numeric<T: Copy>(data: &[u8]) -> Vec<T> {
    let elem_size = mem::size_of::<T>();
    let num_elements = data.len() / elem_size;

    let mut result = Vec::with_capacity(num_elements);

    // SAFETY: We're copying POD types
    unsafe {
        let src_ptr = data.as_ptr() as *const T;
        let dst_ptr = result.as_mut_ptr();
        std::ptr::copy_nonoverlapping(src_ptr, dst_ptr, num_elements);
        result.set_len(num_elements);
    }

    result
}

/// Specialized serializers for common types
pub mod specialized {
    use super::*;

    #[inline]
    pub fn serialize_i64(data: &[i64]) -> Vec<u8> {
        serialize_numeric(data)
    }

    #[inline]
    pub fn serialize_f64(data: &[f64]) -> Vec<u8> {
        serialize_numeric(data)
    }

    #[inline]
    pub fn serialize_i32(data: &[i32]) -> Vec<u8> {
        serialize_numeric(data)
    }

    #[inline]
    pub fn serialize_f32(data: &[f32]) -> Vec<u8> {
        serialize_numeric(data)
    }

    #[inline]
    pub fn deserialize_i64(data: &[u8]) -> Vec<i64> {
        deserialize_numeric(data)
    }

    #[inline]
    pub fn deserialize_f64(data: &[u8]) -> Vec<f64> {
        deserialize_numeric(data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_i64_roundtrip() {
        let data = vec![1i64, 2, 3, 4, 5, 100, 1000, -50];
        let serialized = serialize_numeric(&data);
        let deserialized: Vec<i64> = deserialize_numeric(&serialized);
        assert_eq!(data, deserialized);
    }

    #[test]
    fn test_f64_roundtrip() {
        let data = vec![1.5f64, 2.7, 3.14, -0.5, 1e10];
        let serialized = serialize_numeric(&data);
        let deserialized: Vec<f64> = deserialize_numeric(&serialized);
        assert_eq!(data, deserialized);
    }

    #[test]
    fn test_large_array() {
        let data: Vec<i64> = (0..100_000).collect();
        let serialized = serialize_numeric(&data);
        let deserialized: Vec<i64> = deserialize_numeric(&serialized);
        assert_eq!(data, deserialized);
    }
}
