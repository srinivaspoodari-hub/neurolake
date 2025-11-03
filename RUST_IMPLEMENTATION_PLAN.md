# NCF Rust Implementation Plan (Phase 3 / v2.0)

**Date**: October 31, 2025
**Goal**: Match or beat Parquet performance while maintaining compression advantage
**Target**: 1.5-2M rows/sec write, 2-3M rows/sec read
**Timeline**: 2-3 months

---

## Why Rust?

### Advantages Over Alternatives

| Factor | Rust | C++ | Cython | Python |
|--------|------|-----|--------|--------|
| **Performance** | ✅ Same as C++ | ✅ Maximum | ⚠️ 70-80% | ❌ 10-20% |
| **Memory Safety** | ✅ Guaranteed | ❌ Manual | ⚠️ Partial | ✅ GC |
| **Build System** | ✅ Cargo | ⚠️ CMake | ⚠️ Complex | ✅ pip |
| **Cross-platform** | ✅ Excellent | ⚠️ Tricky | ⚠️ Tricky | ✅ Easy |
| **Python Bindings** | ✅ PyO3 (easy) | ⚠️ pybind11 | ✅ Built-in | ✅ Native |
| **Packaging** | ✅ maturin | ⚠️ Complex | ⚠️ Complex | ✅ pip |
| **Async/Parallel** | ✅ Built-in | ⚠️ Manual | ❌ GIL | ❌ GIL |

**Winner**: Rust provides C++ performance with Python-like developer experience

---

## Architecture Design

### Module Structure

```
neurolake-rust/
├── Cargo.toml              # Rust project config
├── pyproject.toml          # Python packaging
├── src/
│   ├── lib.rs             # Python bindings (PyO3)
│   ├── format/
│   │   ├── mod.rs         # Format module
│   │   ├── schema.rs      # Schema definitions
│   │   ├── writer.rs      # NCF writer (core)
│   │   ├── reader.rs      # NCF reader (core)
│   │   ├── header.rs      # Header serialization
│   │   └── footer.rs      # Footer & checksum
│   ├── serializers/
│   │   ├── mod.rs         # Serializer module
│   │   ├── numeric.rs     # Numeric serialization
│   │   ├── string.rs      # String serialization
│   │   └── stats.rs       # Statistics calculation
│   ├── compression/
│   │   ├── mod.rs         # Compression module
│   │   ├── zstd.rs        # ZSTD compression
│   │   └── parallel.rs    # Parallel compression
│   └── utils/
│       ├── mod.rs         # Utilities
│       ├── buffer.rs      # Buffer management
│       └── checksum.rs    # SHA-256 checksums
└── tests/
    ├── roundtrip_test.rs  # Integration tests
    └── bench_test.rs      # Benchmarks
```

### Core Components

#### 1. Schema System (`schema.rs`)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NCFSchema {
    pub table_name: String,
    pub columns: Vec<ColumnSchema>,
    pub row_count: u64,
    pub version: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnSchema {
    pub name: String,
    pub data_type: NCFDataType,
    pub semantic_type: Option<SemanticType>,
    pub nullable: bool,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum NCFDataType {
    Int8, Int16, Int32, Int64,
    UInt8, UInt16, UInt32, UInt64,
    Float32, Float64,
    String, Binary,
    Date, Timestamp,
}
```

#### 2. Writer (`writer.rs`)

```rust
pub struct NCFWriter {
    file: File,
    schema: NCFSchema,
    compression: CompressionType,
    offsets: HashMap<String, u64>,
    statistics: HashMap<String, ColumnStats>,
}

impl NCFWriter {
    pub fn new(path: &Path, schema: NCFSchema) -> Result<Self>;
    pub fn write(&mut self, data: DataFrame) -> Result<()>;
    pub fn flush(&mut self) -> Result<()>;
}
```

#### 3. Serializers (`serializers/`)

```rust
// Numeric serialization (zero-copy)
pub fn serialize_numeric<T: NumericType>(
    data: &[T],
    buffer: &mut Vec<u8>
) -> Result<()>;

// String serialization (optimized)
pub fn serialize_strings(
    data: &[String],
    buffer: &mut Vec<u8>
) -> Result<()>;

// Statistics (single-pass)
pub fn calculate_stats<T>(data: &[T]) -> ColumnStats;
```

#### 4. Compression (`compression/`)

```rust
// Parallel ZSTD compression
pub fn compress_parallel(
    data: &[u8],
    level: i32,
    num_threads: usize
) -> Result<Vec<u8>>;

// Column-wise parallel compression
pub fn compress_columns_parallel(
    columns: Vec<Vec<u8>>
) -> Result<Vec<Vec<u8>>>;
```

---

## Implementation Phases

### Week 1: Foundation

**Goal**: Set up Rust project and basic structure

**Tasks**:
1. Initialize Cargo project with PyO3
2. Set up maturin for Python packaging
3. Implement schema system
4. Implement header/footer serialization
5. Add basic file I/O

**Deliverables**:
- Working Rust project
- Python bindings scaffold
- Basic file format (no data yet)

### Week 2: Core Serialization

**Goal**: Implement high-performance serialization

**Tasks**:
1. Numeric serialization (zero-copy)
2. String serialization (optimized)
3. Statistics calculation (single-pass)
4. Buffer management
5. Unit tests for serializers

**Deliverables**:
- Fast numeric serialization
- Optimized string serialization
- Statistics calculator
- Full test coverage

### Week 3: Compression & Writer

**Goal**: Complete NCF writer with compression

**Tasks**:
1. ZSTD compression integration
2. Parallel compression (multi-threaded)
3. Complete NCF writer
4. Checksum calculation
5. Integration tests

**Deliverables**:
- Working NCF writer
- Parallel compression
- Data integrity (checksums)
- Write benchmarks

### Week 4: Reader & Python Bindings

**Goal**: Complete reader and Python integration

**Tasks**:
1. NCF reader implementation
2. Decompression (parallel)
3. PyO3 Python bindings
4. maturin packaging
5. Python API tests

**Deliverables**:
- Working NCF reader
- Full Python API
- Installable wheel
- Python integration tests

### Week 5: Optimization & Benchmarking

**Goal**: Optimize and validate performance

**Tasks**:
1. Profile and optimize hot paths
2. SIMD optimizations
3. Memory optimization
4. Comprehensive benchmarks
5. Documentation

**Deliverables**:
- Optimized implementation
- Benchmark results
- Performance documentation
- API documentation

### Week 6: Production Hardening

**Goal**: Production-ready implementation

**Tasks**:
1. Error handling improvements
2. Edge case testing
3. Memory leak testing
4. Cross-platform validation
5. Release preparation

**Deliverables**:
- Production-ready code
- Full test coverage
- Cross-platform wheels
- Release v2.0

---

## Performance Targets

### Write Performance

| Metric | Target | Current v1.1 | Improvement |
|--------|--------|--------------|-------------|
| **Numeric serialization** | 5-10 GB/s | ~2 GB/s | 2.5-5x |
| **String serialization** | 2-5 GB/s | ~0.5 GB/s | 4-10x |
| **Compression (ZSTD)** | 1-2 GB/s | ~0.8 GB/s | 1.25-2.5x |
| **Overall write** | 1.5-2M rows/s | 949K rows/s | 1.6-2.1x |

### Read Performance

| Metric | Target | Current v1.1 | Improvement |
|--------|--------|--------------|-------------|
| **Decompression** | 3-5 GB/s | ~2 GB/s | 1.5-2.5x |
| **Deserialization** | 10-20 GB/s | ~5 GB/s | 2-4x |
| **Overall read** | 2-3M rows/s | 460K rows/s | 4-6x |

### Compression

| Metric | Target | Current v1.1 | Improvement |
|--------|--------|--------------|-------------|
| **Compression ratio** | 12-15x | 10x | 1.2-1.5x |
| **vs Parquet** | 1.8-2x smaller | 1.54x smaller | Maintain/improve |

---

## Technical Approach

### 1. Zero-Copy Serialization

```rust
// Direct memory access, no copies
pub fn serialize_numeric_zero_copy<T: Pod>(
    data: &[T]
) -> &[u8] {
    // Cast slice to bytes (zero-copy)
    unsafe {
        std::slice::from_raw_parts(
            data.as_ptr() as *const u8,
            data.len() * std::mem::size_of::<T>()
        )
    }
}
```

### 2. SIMD Optimizations

```rust
// Use SIMD for min/max calculations
#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

pub fn min_max_simd(data: &[f64]) -> (f64, f64) {
    unsafe {
        // Use AVX2 for 4x speedup
        // Process 4 f64s at once
    }
}
```

### 3. Parallel Compression

```rust
use rayon::prelude::*;

pub fn compress_columns_parallel(
    columns: Vec<Vec<u8>>
) -> Result<Vec<Vec<u8>>> {
    columns
        .par_iter()  // Parallel iterator
        .map(|col| compress_single(col))
        .collect()
}
```

### 4. Memory Pool

```rust
// Reuse buffers to reduce allocations
pub struct BufferPool {
    pools: Vec<Mutex<Vec<Vec<u8>>>>,
}

impl BufferPool {
    pub fn get_buffer(&self, size: usize) -> Vec<u8> {
        // Get from pool or allocate new
    }

    pub fn return_buffer(&self, buf: Vec<u8>) {
        // Return to pool for reuse
    }
}
```

---

## Dependencies

### Rust Crates

```toml
[dependencies]
# Python bindings
pyo3 = { version = "0.20", features = ["extension-module"] }

# Serialization
serde = { version = "1.0", features = ["derive"] }
rmp-serde = "1.1"  # MessagePack

# Compression
zstd = "0.13"
lz4 = "1.24"

# Parallelism
rayon = "1.8"
crossbeam = "0.8"

# Utilities
sha2 = "0.10"  # SHA-256
byteorder = "1.5"
memmap2 = "0.9"  # Memory-mapped files

# Arrow integration (optional)
arrow = { version = "50", optional = true }

[dev-dependencies]
criterion = "0.5"  # Benchmarking
proptest = "1.4"   # Property testing
```

### Build Tools

```toml
[build-dependencies]
pyo3-build-config = "0.20"

[tool.maturin]
python-source = "python"
module-name = "neurolake._ncf_rust"
```

---

## Testing Strategy

### Unit Tests (Rust)

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_numeric_serialization() {
        let data = vec![1i64, 2, 3, 4, 5];
        let serialized = serialize_numeric(&data).unwrap();
        let deserialized = deserialize_numeric(&serialized).unwrap();
        assert_eq!(data, deserialized);
    }

    #[test]
    fn test_string_serialization() {
        let data = vec!["hello", "world", "test"];
        let serialized = serialize_strings(&data).unwrap();
        let deserialized = deserialize_strings(&serialized).unwrap();
        assert_eq!(data, deserialized);
    }
}
```

### Integration Tests (Python)

```python
def test_rust_writer():
    """Test Rust NCF writer"""
    data = pd.DataFrame({
        'id': range(100000),
        'value': np.random.rand(100000),
        'name': [f'user_{i}' for i in range(100000)]
    })

    # Write with Rust
    ncf.write_rust('test.ncf', data, schema)

    # Read back
    result = ncf.read('test.ncf')

    # Verify
    assert result.equals(data)
```

### Benchmarks (Criterion)

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_write(c: &mut Criterion) {
    let data = create_test_data(100_000);

    c.bench_function("ncf_rust_write_100k", |b| {
        b.iter(|| {
            write_ncf(black_box(&data))
        });
    });
}

criterion_group!(benches, bench_write);
criterion_main!(benches);
```

---

## Build & Packaging

### Development Build

```bash
# Install Rust (if not installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install maturin
pip install maturin

# Build for development
maturin develop --release

# Run tests
cargo test
pytest tests/
```

### Production Wheels

```bash
# Build wheel for current platform
maturin build --release

# Build for multiple platforms (GitHub Actions)
maturin build --release --target x86_64-unknown-linux-gnu
maturin build --release --target x86_64-pc-windows-msvc
maturin build --release --target x86_64-apple-darwin
maturin build --release --target aarch64-apple-darwin
```

---

## API Design

### Python API (Same as v1.1)

```python
from neurolake.ncf import NCFWriter, NCFReader, NCFSchema, ColumnSchema, NCFDataType

# Create schema
schema = NCFSchema(
    table_name="users",
    columns=[
        ColumnSchema(name="id", data_type=NCFDataType.INT64),
        ColumnSchema(name="name", data_type=NCFDataType.STRING),
    ]
)

# Write (uses Rust internally)
with NCFWriter("users.ncf", schema) as writer:
    writer.write(dataframe)

# Read (uses Rust internally)
with NCFReader("users.ncf") as reader:
    df = reader.read()
```

**Key Point**: Same API as v1.1, but 2-3x faster!

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **Rust learning curve** | Start with small modules, use examples |
| **PyO3 complexity** | Follow official guides, use maturin |
| **Performance not achieved** | Profile early, optimize incrementally |
| **Cross-platform issues** | Test on CI/CD (GitHub Actions) |
| **Memory safety bugs** | Extensive testing, use unsafe sparingly |

### Project Risks

| Risk | Mitigation |
|------|------------|
| **Timeline slippage** | Weekly milestones, MVP approach |
| **Resource constraints** | Focus on core features first |
| **Integration issues** | Keep Python API compatible |
| **Adoption resistance** | Maintain fallback to v1.1 |

---

## Success Criteria

### Must Have (MVP)

- ✅ Write performance: 1.5M rows/sec minimum
- ✅ Read performance: 2M rows/sec minimum
- ✅ Compression: Match or beat v1.1 (1.54x vs Parquet)
- ✅ API compatibility: Same as v1.1
- ✅ Data integrity: SHA-256 checksums
- ✅ Test coverage: 90%+ for core modules

### Should Have

- ⚠️ Parallel compression: Multi-threaded
- ⚠️ Arrow integration: Zero-copy with Arrow
- ⚠️ SIMD optimizations: For numeric operations
- ⚠️ Memory efficiency: <10MB overhead

### Nice to Have

- ⏳ Streaming read/write
- ⏳ Dictionary encoding
- ⏳ Null bitmap encoding
- ⏳ Predicate pushdown

---

## Timeline

### Detailed Schedule

| Week | Focus | Deliverables |
|------|-------|--------------|
| **1** | Foundation | Project setup, schema system |
| **2** | Serialization | Numeric & string serializers |
| **3** | Writer | Complete writer + compression |
| **4** | Reader | Complete reader + bindings |
| **5** | Optimization | Performance tuning |
| **6** | Production | Testing & release |

### Milestones

- **Week 2**: First benchmark (serialization only)
- **Week 3**: First write benchmark (full stack)
- **Week 4**: First read benchmark + Python API
- **Week 5**: Performance targets met
- **Week 6**: Release v2.0

---

## Conclusion

**Rust implementation will deliver:**

✅ **1.5-2M rows/sec write** (2x faster than v1.1)
✅ **2-3M rows/sec read** (4-6x faster than v1.1)
✅ **Match or beat Parquet** on performance
✅ **Maintain compression advantage** (1.8-2x vs Parquet)
✅ **Production-ready** native implementation

**Next Steps**:
1. Set up Rust project
2. Implement core serializers
3. Build and benchmark
4. Deploy v2.0

---

*Last Updated*: October 31, 2025
*Status*: Design Complete, Ready to Implement
*Timeline*: 6 weeks to v2.0 release
