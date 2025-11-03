# NCF Performance Analysis & Optimization Plan

**Date**: October 31, 2025
**Version**: NCF v1.0
**Status**: Performance Bottlenecks Identified

---

## Executive Summary

### Current Performance (50,000 rows)

| Metric | NCF v1.0 | Parquet (Snappy) | Gap |
|--------|----------|------------------|-----|
| **Write Speed** | 241K rows/sec | 961K rows/sec | **4.0x slower** |
| **Read Speed** | 460K rows/sec | 885K rows/sec | **1.9x slower** |
| **File Size** | 0.96 MB | 1.48 MB | **1.53x smaller** ✅ |

**Conclusion**: NCF achieves better compression but significantly slower performance than Parquet.

---

## Why is Parquet Faster?

### 1. **Implementation Language** (PRIMARY FACTOR)

| Aspect | Parquet | NCF | Impact |
|--------|---------|-----|--------|
| Core | C++ (Apache Arrow) | Pure Python | **10-100x** |
| Serialization | Optimized C++ | Python loops | **10-50x** |
| Compression | Native Snappy (C++) | Python ZSTD bindings | **2-5x** |
| Memory Management | Zero-copy | Python object overhead | **2-5x** |

**Impact**: C++ is fundamentally faster for CPU-intensive operations like compression and serialization.

### 2. **String Serialization** (BIGGEST BOTTLENECK)

**NCF Current Implementation** (Python):
```python
# For each string column (3 columns with 50K values each = 150K strings)
string_list = [str(s).encode('utf-8') for s in col_data]  # 150K encode() calls
offsets = [0]
for s in string_list:
    offsets.append(offsets[-1] + len(s))  # 150K append() calls

result = struct.pack("<I", num_strings)
result += struct.pack(f"<{len(offsets)}I", *offsets)  # Pack 150K offsets
result += b"".join(string_list)  # Join 150K strings
```

**Performance Profile Results**:
- `encode()`: 150,011 calls, 0.015s
- `append()`: 150,007 calls, 0.012s
- `join()`: 0.004s
- **Total string serialization: ~0.062s (30% of write time)**

**Parquet Implementation** (C++):
- Single memory allocation
- Vectorized operations
- Zero-copy where possible
- **Estimated: 0.005s (10x faster)**

### 3. **Statistics Generation** (SECOND BOTTLENECK)

**NCF Profile Results**:
- `_generate_statistics()`: 0.025s (12% of write time)
- Includes `numpy.unique()` calls: 0.039s total

**Why Slow**:
```python
for col in columns:
    unique_count = len(np.unique(col_data))  # Expensive sort operation
    min_val = np.min(col_data)
    max_val = np.max(col_data)
    # ... more calculations
```

**Optimization Opportunity**: Calculate statistics during serialization (single pass).

### 4. **Compression** (MEDIUM IMPACT)

**NCF**:
- ZSTD compression level 3
- Python bindings with some overhead
- Time: 0.007s (3% of write time)

**Parquet**:
- Snappy compression (faster but lower ratio)
- Native C++ implementation
- Faster but produces larger files

**Trade-off**: NCF prioritizes compression ratio, Parquet prioritizes speed.

---

## Profiling Results Breakdown

### NCF Write Profile (Top Operations)

| Operation | Time | % of Total | Calls | Bottleneck? |
|-----------|------|------------|-------|-------------|
| `_serialize_column()` | 0.105s | 51% | 6 | ✅ YES |
| `_generate_statistics()` | 0.088s | 43% | 1 | ✅ YES |
| `unique()` calls | 0.039s | 19% | 6 | ✅ YES |
| String `encode()` | 0.015s | 7% | 150K | ⚠️ Medium |
| String `append()` | 0.012s | 6% | 150K | ⚠️ Medium |
| Compression | 0.007s | 3% | 6 | ❌ No |

**Key Insight**: 94% of time spent in serialization and statistics (both Python-heavy operations).

### NCF Read Profile (Top Operations)

| Operation | Time | % of Total | Calls | Bottleneck? |
|-----------|------|------------|-------|-------------|
| `_deserialize_column()` | 0.077s | 71% | 6 | ✅ YES |
| String `decode()` | 0.017s | 16% | 150K | ⚠️ Medium |
| `open()` file | 0.021s | 19% | 1 | ❌ No (I/O) |
| Decompression | 0.003s | 3% | 6 | ❌ No |
| DataFrame creation | 0.004s | 4% | 1 | ❌ No |

**Key Insight**: String deserialization dominates (71% of time).

---

## Optimization Strategies

### Phase 1: Quick Python Wins (Target: 2-3x speedup)

#### 1.1 Optimize String Serialization (Expected: 2x)

**Current Problem**: Python loop with repeated allocations

**Solution**: Pre-calculate sizes and use numpy arrays
```python
def _serialize_strings_fast(col_data):
    """Optimized string serialization"""
    # Convert to bytes array upfront
    string_bytes = np.array([s.encode('utf-8') for s in col_data], dtype=object)

    # Calculate offsets vectorized
    lengths = np.array([len(s) for s in string_bytes], dtype=np.uint32)
    offsets = np.concatenate(([0], np.cumsum(lengths)))

    # Pre-allocate buffer
    total_size = 4 + len(offsets) * 4 + offsets[-1]
    buffer = bytearray(total_size)

    # Pack header
    struct.pack_into("<I", buffer, 0, len(string_bytes))

    # Pack offsets
    struct.pack_into(f"<{len(offsets)}I", buffer, 4, *offsets)

    # Copy strings (single operation)
    pos = 4 + len(offsets) * 4
    for s in string_bytes:
        buffer[pos:pos+len(s)] = s
        pos += len(s)

    return bytes(buffer)
```

**Expected Impact**: 0.062s → 0.030s (saves 0.032s, 15% of total time)

#### 1.2 Single-Pass Statistics (Expected: 1.5x)

**Current Problem**: Separate pass for statistics

**Solution**: Calculate during serialization
```python
def _serialize_column_with_stats(col_data, col_schema):
    """Serialize and calculate stats in one pass"""
    # Initialize stats
    stats = {
        'min': None, 'max': None, 'null_count': 0,
        'distinct_count': None  # Approximate with HyperLogLog
    }

    # For numeric columns
    if is_numeric(col_schema):
        stats['min'] = col_data.min()  # Already fast
        stats['max'] = col_data.max()
        stats['null_count'] = pd.isna(col_data).sum()
        # Skip unique() - too expensive, use approximation

    # Serialize
    serialized = col_data.astype(target_dtype).tobytes()

    return serialized, stats
```

**Expected Impact**: 0.039s → 0.010s (saves 0.029s, 14% of total time)

#### 1.3 Lower Compression Level (Expected: 1.3x)

**Current**: ZSTD level 3
**Proposed**: ZSTD level 1

**Trade-off**:
- Speed: 1.3x faster compression
- File size: 5-10% larger

**Expected Impact**: 0.007s → 0.005s (saves 0.002s, minor but easy)

#### 1.4 Reduce Unnecessary Operations

- Cache schema lookups
- Use memoryview for zero-copy operations
- Avoid repeated dtype checks

**Expected Impact**: 5-10% speedup

### Phase 1 Total Expected Impact: **2-3x speedup**

---

### Phase 2: Cython Acceleration (Target: 3-5x total speedup)

Rewrite hot paths in Cython:
1. String serialization/deserialization
2. Statistics calculation
3. Column serialization loop

**Expected Impact**: 2-3x on top of Phase 1 = **3-5x total**

**Effort**: Medium (1-2 weeks)

---

### Phase 3: Parallel Processing (Target: 5-7x total speedup)

**Strategy**: Process columns in parallel

```python
from concurrent.futures import ThreadPoolExecutor

def _write_column_data_parallel(self, columns):
    """Parallel column compression"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for col_name in columns:
            future = executor.submit(self._serialize_and_compress, col_name, columns[col_name])
            futures.append(future)

        results = [f.result() for f in futures]
```

**Expected Impact**: 1.5-2x on top of Phase 2 = **5-7x total**

**Limitation**: Python GIL limits benefit (need Cython/C++ for full parallelism)

---

### Phase 4: Rust/C++ Rewrite (Target: Match Parquet)

**Goal**: Full C++/Rust implementation with Arrow integration

**Expected Performance**:
- Write: 800K-1M rows/sec (4x faster than current)
- Read: 800K-1M rows/sec (2x faster than current)
- File size: Maintain 1.5x advantage

**Effort**: Large (2-3 months)

**Technologies**:
- Rust with PyO3 bindings
- Apache Arrow for zero-copy interop
- Native ZSTD compression

---

## Recommended Action Plan

### Immediate (This Week)

✅ **Completed**:
1. Profile NCF performance
2. Identify bottlenecks
3. Document optimization opportunities

🔧 **Next**:
1. Implement Phase 1 optimizations (2-3 days)
2. Benchmark improvements
3. Document results

### Short-term (Next 2 Weeks)

1. Implement Cython acceleration (Phase 2)
2. Add parallel processing (Phase 3)
3. Target: 5-7x speedup = 1.2-1.7M rows/sec write speed

### Medium-term (Next 2 Months)

1. Evaluate Rust vs C++ for rewrite
2. Design Arrow-native API
3. Prototype core serialization in Rust

### Long-term (Months 3-6)

1. Full Rust/C++ implementation
2. Match or exceed Parquet performance
3. Maintain compression advantage

---

## Performance Targets

### NCF v1.1 (Python Optimizations)

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Write | 241K rows/sec | 600-700K rows/sec | **2.5-3x** |
| Read | 460K rows/sec | 1M rows/sec | **2x** |
| Compression | 1.53x | 1.53x | Maintain |

### NCF v2.0 (Rust/C++ Rewrite)

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Write | 241K rows/sec | 1.5-2M rows/sec | **6-8x** |
| Read | 460K rows/sec | 2-3M rows/sec | **4-6x** |
| Compression | 1.53x | 1.8-2.0x | **Better** |

**Goal**: Beat Parquet on ALL metrics (speed + compression)

---

## Technical Debt

### Current Limitations

1. **Pure Python implementation** - Fundamental speed limit
2. **No dictionary encoding** - Missing 10-100x compression for low-cardinality strings
3. **No parallel compression** - Not using multi-core CPUs
4. **Expensive unique() calls** - Statistics calculation is slow
5. **No null bitmap** - Inefficient NULL handling

### Must Fix for Production

1. ✅ Dtype conversion bug (FIXED)
2. ✅ Checksum validation (FIXED)
3. ⏳ Dictionary encoding (v1.1)
4. ⏳ Null bitmap encoding (v1.1)
5. ⏳ Performance optimizations (v1.1-v2.0)

---

## Comparison with Industry Standards

### Apache Parquet (Current Leader)

| Aspect | Parquet | NCF v1.0 | NCF v2.0 (Target) |
|--------|---------|----------|-------------------|
| Implementation | C++ | Python | Rust/C++ |
| Write Speed | 960K rows/sec | 241K rows/sec | 1.5-2M rows/sec |
| Read Speed | 885K rows/sec | 460K rows/sec | 2-3M rows/sec |
| Compression | Baseline | 1.53x better | 1.8-2x better |
| AI Features | None | Semantic types | Learned indexes |
| Maturity | 10+ years | New | New |

### Why NCF Can Win Long-term

1. **AI-Native Design**: Semantic types, learned indexes
2. **Better Compression**: Already 1.53x, targeting 2x
3. **Modern Stack**: Rust = fast + safe
4. **Purpose-Built**: Designed for ML workflows, not legacy Hadoop

---

## Conclusion

**Current State**: NCF v1.0 is **functionally correct** but **4x slower than Parquet** due to pure Python implementation.

**Path Forward**:
1. **Phase 1** (immediate): Python optimizations → 2-3x speedup
2. **Phase 2** (short-term): Cython + parallel → 5-7x speedup
3. **Phase 3** (long-term): Rust/C++ rewrite → Match/beat Parquet

**Realistic Timeline**:
- v1.1 (Python optimized): 2-3 weeks
- v1.2 (Cython + parallel): 1-2 months
- v2.0 (Rust/C++ rewrite): 3-6 months

**Bottom Line**: NCF has the right design and better compression. Performance is solvable with implementation improvements. The Python prototype successfully validated the format design.

---

*Last Updated*: October 31, 2025
*Status*: Bottlenecks identified, optimization plan ready
