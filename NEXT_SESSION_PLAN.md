# Next Session: Complete NCF Rust v2.0

## 🎯 Current Status

**GOOD NEWS**: Rust NCF v2.0 builds successfully!
- ✅ 29/29 unit tests passing
- ✅ Python bindings working
- ✅ All serializers implemented
- ✅ Compression engine ready

**WHAT'S LEFT**: Complete the write() and read() methods (8-10 hours)

---

## 📋 Task List

### Session Goal: Implement Writer.write() method (2-4 hours)

**Location**: `core/ncf-rust/src/format/writer.rs`

#### Step 1: Accept Python Data
```rust
pub fn write(&mut self, py: Python, data: PyObject) -> PyResult<()> {
    // Convert PyObject to DataFrame or dict
    // Extract column data
}
```

#### Step 2: Process Each Column
```rust
// Already implemented! Just need to call:
for (col_schema, col_data) in columns {
    let column_result = match col_schema.data_type {
        NCFDataType::Int64 => self.process_i64_column(data),
        NCFDataType::Float64 => self.process_f64_column(data),
        NCFDataType::String => self.process_string_column(data),
        // ... etc
    };
}
```

#### Step 3: Write to File
```rust
// Write magic bytes
self.file.write_all(b"NCF\x01")?;

// Write version
self.file.write_all(&1u32.to_le_bytes())?;

// Write schema (already have to_msgpack!)
let schema_bytes = self.schema.to_msgpack()?;
// ... write schema_bytes

// Write compressed column data
// ... already compressed from step 2!

// Write footer with checksum
```

#### Step 4: Test It
```python
import pandas as pd
from ncf_rust import NCFWriter, NCFSchema, ColumnSchema, NCFDataType

# Create test data
df = pd.DataFrame({
    'id': [1, 2, 3],
    'name': ['Alice', 'Bob', 'Charlie']
})

# Create schema
schema = NCFSchema("test", [
    ColumnSchema("id", NCFDataType.int64(), None, True),
    ColumnSchema("name", NCFDataType.string(), None, True)
], 0, 1)

# Write
writer = NCFWriter("test.ncf", schema)
writer.write(df)  # <-- This should work!
```

---

### Session Goal: Implement Reader.read() method (2-4 hours)

**Location**: `core/ncf-rust/src/format/reader.rs`

#### Step 1: Read File Header
```rust
pub fn read(&mut self, py: Python) -> PyResult<PyObject> {
    // Read and validate magic bytes
    let mut magic = [0u8; 4];
    self.file.read_exact(&mut magic)?;
    assert_eq!(&magic, b"NCF\x01");

    // Read version
    // Read schema using from_msgpack!
}
```

#### Step 2: Read Column Data
```rust
// Read compressed column data
// Decompress (already have decompress!)
// Deserialize based on type
```

#### Step 3: Convert to Python
```rust
// Create Python dict
let result = PyDict::new(py);
result.set_item("id", id_column)?;
result.set_item("name", name_column)?;
Ok(result.into())
```

#### Step 4: Test It
```python
from ncf_rust import NCFReader

# Read
reader = NCFReader("test.ncf")
result = reader.read()

# Verify
assert result['id'] == [1, 2, 3]
assert result['name'] == ['Alice', 'Bob', 'Charlie']
```

---

### Session Goal: End-to-End Testing (1-2 hours)

#### Test 1: Roundtrip
```python
# Write then read, verify data unchanged
original_df = create_test_data(10000)
write_and_read(original_df)
assert_frame_equal(original_df, result_df)
```

#### Test 2: Large Dataset
```python
# 100K rows
large_df = create_test_data(100000)
write_and_read(large_df)
```

#### Test 3: Mixed Types
```python
# int, float, string
mixed_df = pd.DataFrame({
    'int_col': range(1000),
    'float_col': np.random.randn(1000),
    'str_col': ['test'] * 1000
})
write_and_read(mixed_df)
```

---

### Session Goal: Benchmarking (1 hour)

Run the existing benchmark:
```bash
python tests/benchmark_rust_vs_python.py
```

**Expected Results**:
- Python NCF v1.1: ~950K rows/sec
- **Rust NCF v2.0: 1.5-2M rows/sec** ⚡
- Parquet: ~1.67M rows/sec

**Success Criteria**: Rust should be 1.5-2x faster than Python!

---

## 🔧 Quick Start Commands

### Open the files to edit:
```bash
# Writer
code core/ncf-rust/src/format/writer.rs

# Reader
code core/ncf-rust/src/format/reader.rs
```

### Build and test as you go:
```bash
# Build
cd core/ncf-rust
cargo build --release

# Test
cargo test --release

# Install Python extension
../../.venv/Scripts/maturin develop --release

# Test import
python -c "import ncf_rust; print('OK')"
```

---

## 💡 Implementation Tips

### Tip 1: Look at Python NCF v1.1 for Reference
The Python implementation in `neurolake/ncf/format/writer.py` and `reader.py` already does everything you need. You can copy the logic and translate to Rust.

### Tip 2: Use Existing Helper Methods
You've already implemented:
- ✅ `process_i64_column()`
- ✅ `process_f64_column()`
- ✅ `process_string_column()`
- ✅ `to_msgpack()` / `from_msgpack()`
- ✅ `compress()` / `decompress()`

Just call them in the right order!

### Tip 3: Start Simple
First implementation:
1. Write only ONE column (int64)
2. Read it back
3. Verify correctness
4. THEN add more types

### Tip 4: Add Lots of Print Statements
```rust
eprintln!("Writing schema, size: {}", schema_bytes.len());
eprintln!("Compressed column 0 to {} bytes", compressed.len());
```

Helps debug issues quickly!

---

## 📊 Progress Tracking

Create a simple checklist:

```markdown
### Writer.write() Implementation
- [ ] Accept Python DataFrame
- [ ] Extract column data
- [ ] Call process_*_column methods
- [ ] Write magic + version
- [ ] Write schema (msgpack)
- [ ] Write column data
- [ ] Write footer
- [ ] Test with simple data

### Reader.read() Implementation
- [ ] Validate magic bytes
- [ ] Read version
- [ ] Deserialize schema (msgpack)
- [ ] Read column data
- [ ] Decompress columns
- [ ] Deserialize to Python
- [ ] Return dict/DataFrame
- [ ] Test roundtrip

### Testing
- [ ] Roundtrip test passing
- [ ] Large dataset (100K rows)
- [ ] Mixed data types
- [ ] Benchmark shows 1.5-2x speedup
```

---

## 🎯 Definition of Done

When you can run this successfully:

```python
import pandas as pd
from ncf_rust import NCFWriter, NCFReader, NCFSchema, ColumnSchema, NCFDataType

# Create data
df = pd.DataFrame({
    'id': range(100000),
    'value': np.random.randn(100000),
    'name': ['test'] * 100000
})

# Create schema
schema = NCFSchema("benchmark", [
    ColumnSchema("id", NCFDataType.int64(), None, True),
    ColumnSchema("value", NCFDataType.float64(), None, True),
    ColumnSchema("name", NCFDataType.string(), None, True),
], 0, 1)

# Write
import time
start = time.time()
writer = NCFWriter("test.ncf", schema)
writer.write(df)
write_time = time.time() - start

# Read
start = time.time()
reader = NCFReader("test.ncf")
result = reader.read()
read_time = time.time() - start

# Verify
assert len(result['id']) == 100000
print(f"Write: {len(df) / write_time:,.0f} rows/sec")
print(f"Read: {len(df) / read_time:,.0f} rows/sec")
print("✅ NCF Rust v2.0 is COMPLETE!")
```

**Target**:
- Write speed: 1.5-2M rows/sec
- Read speed: 1.5-2M rows/sec
- 1.5-2x faster than Python NCF v1.1

---

## 📚 Reference Files

### Look at these for guidance:
1. **Python Writer**: `neurolake/ncf/format/writer.py`
   - Shows the complete file format
   - Header/footer structure
   - Write order

2. **Python Reader**: `neurolake/ncf/format/reader.py`
   - How to read the format
   - Deserialization logic

3. **Rust Serializers**: `core/ncf-rust/src/serializers/`
   - Already working perfectly!
   - Just call them from write()

4. **Rust Tests**: `core/ncf-rust/src/format/writer.rs` (bottom)
   - Test examples showing how to use the API

---

## 🚀 You Got This!

The foundation is solid:
- ✅ All the hard optimization work is done
- ✅ Serializers work perfectly
- ✅ Compression works perfectly
- ✅ Tests pass

All that's left is connecting the pieces together. It's mostly straightforward glue code!

**Estimated Time**: 8-10 focused hours
**Difficulty**: Medium (requires understanding the file format)
**Reward**: 1.5-2x performance improvement! 🎉

---

**Good luck! You're 80% done already!** 💪

---

Last Updated: November 1, 2025
