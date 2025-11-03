# NCF Format Specification v1.0

**NeuroCell Format (NCF) - AI-Native Columnar Storage**

**Version**: 1.0
**Date**: October 31, 2025
**Status**: Draft
**Authors**: NeuroLake Team

---

## Table of Contents

1. [Overview](#overview)
2. [Design Goals](#design-goals)
3. [File Structure](#file-structure)
4. [Data Types](#data-types)
5. [Compression](#compression)
6. [Learned Indexes](#learned-indexes)
7. [Column Groups](#column-groups)
8. [Semantic Metadata](#semantic-metadata)
9. [Example](#example)

---

## 1. Overview

NCF (NeuroCell Format) is a columnar storage format optimized for AI workloads. Unlike traditional formats (Parquet, ORC), NCF uses:

- **Neural Compression**: ML models learn data-specific patterns for 12-15x compression
- **Learned Indexes**: ML models replace B-trees for 100x size reduction
- **Semantic Metadata**: AI agents understand data meaning and context
- **Column Groups**: Optimized layout based on access patterns

### Key Features

| Feature | Traditional (Parquet) | NCF |
|---------|---------------------|-----|
| Compression Ratio | 10x | 12-15x |
| Index Size | 10-20% of data | 0.1% of data |
| AI-Aware Metadata | No | Yes |
| Learned Patterns | No | Yes |

---

## 2. Design Goals

### Primary Goals

1. **Maximum Compression**: Achieve 12-15x compression through learned patterns
2. **Fast Queries**: 2-5x faster point queries using learned indexes
3. **AI Integration**: Semantic metadata for AI agent understanding
4. **Compatibility**: Support standard DataFrames (pandas, polars)

### Non-Goals

1. **Random Writes**: NCF is write-once, read-many (like Parquet)
2. **Row-Based Access**: Optimized for columnar analytical queries
3. **Streaming**: Designed for batch processing, not streaming

---

## 3. File Structure

### 3.1 Overall Layout

```
┌─────────────────────────────────────────────────────────────┐
│                      NCF File (.ncf)                        │
├─────────────────────────────────────────────────────────────┤
│  Section 1: Magic Number & Version              (8 bytes)  │
│  Section 2: File Header                         (Variable) │
│  Section 3: Schema Definition                   (Variable) │
│  Section 4: Statistics Block                    (Variable) │
│  Section 5: Learned Indexes Section             (Variable) │
│  Section 6: Column Groups Data                  (Variable) │
│  Section 7: Footer & Offset Index               (Variable) │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Section Descriptions

#### Section 1: Magic Number & Version (8 bytes)

```
Offset  Size  Description
------  ----  -----------
0       4     Magic number: "NCF\x01" (0x4E 0x43 0x46 0x01)
4       4     Format version: uint32 little-endian (currently 1)
```

**Purpose**: File type identification and version validation

**Validation**:
```python
magic = file.read(4)
if magic != b"NCF\x01":
    raise ValueError("Not a valid NCF file")

version = struct.unpack("<I", file.read(4))[0]
if version != 1:
    raise ValueError(f"Unsupported NCF version: {version}")
```

#### Section 2: File Header (Variable)

```
Offset  Size      Description
------  --------  -----------
8       4         Header length (uint32)
12      4         Schema offset (uint32)
16      4         Statistics offset (uint32)
20      4         Indexes offset (uint32)
24      4         Data offset (uint32)
28      4         Footer offset (uint32)
32      8         Total row count (uint64)
40      8         Created timestamp (uint64)
48      8         Modified timestamp (uint64)
56      1         Compression algorithm (uint8)
                  0=None, 1=ZSTD, 2=LZ4, 3=Neural
57      1         Encryption enabled (uint8)
58      2         Reserved for future use
```

**Total Header Size**: 60 bytes

#### Section 3: Schema Definition (Variable)

Stored as **msgpack-encoded** JSON for efficiency:

```json
{
  "table_name": "users",
  "version": 1,
  "row_count": 1000000,
  "columns": [
    {
      "name": "id",
      "data_type": "int64",
      "nullable": false,
      "semantic_type": "id_key",
      "compression_model": null,
      "use_dictionary": false,
      "create_learned_index": true,
      "index_model_type": "rmi",
      "contains_pii": false,
      "column_group": 0
    },
    {
      "name": "email",
      "data_type": "string",
      "nullable": true,
      "semantic_type": "pii_email",
      "compression_model": "email_autoencoder_v1",
      "use_dictionary": true,
      "create_learned_index": false,
      "contains_pii": true,
      "column_group": 1
    }
  ],
  "column_groups": {
    "0": ["id"],
    "1": ["email", "name"]
  }
}
```

**Encoding**: msgpack (more compact than JSON)
**Size**: Typically 1-10 KB

#### Section 4: Statistics Block (Variable)

Per-column statistics for query optimization:

```
For each column:
  Column Name (variable, null-terminated string)
  Min Value (variable, depends on data type)
  Max Value (variable, depends on data type)
  Null Count (8 bytes, uint64)
  Distinct Count (8 bytes, uint64)
  Total Count (8 bytes, uint64)
  Avg Length (8 bytes, float64, for strings/binary)
```

**Purpose**: Enable predicate pushdown and query optimization

**Example**:
```python
{
  "id": {
    "min": 1,
    "max": 1000000,
    "null_count": 0,
    "distinct_count": 1000000,
    "total_count": 1000000
  },
  "email": {
    "min": "aaa@example.com",
    "max": "zzz@example.com",
    "null_count": 150,
    "distinct_count": 999850,
    "total_count": 1000000,
    "avg_length": 25.3
  }
}
```

#### Section 5: Learned Indexes Section (Variable)

Contains ML model weights for learned indexes:

```
For each indexed column:
  Column Name (variable, null-terminated string)
  Index Model Type (1 byte)
    0=None, 1=RMI, 2=PGM, 3=RadixSpline
  Model Size (4 bytes, uint32)
  Model Data (variable, serialized PyTorch/ONNX model)
    - For RMI: Root model + leaf models
    - For PGM: Segments + slopes
  Index Metadata (variable, msgpack)
    - Error bounds
    - Block mappings
    - Fallback B-tree (if needed)
```

**Purpose**: Fast data location prediction without scanning

**Example RMI Structure**:
```python
{
  "column": "id",
  "model_type": "rmi",
  "error_bound": 100,  # Max prediction error
  "root_model": {
    "type": "linear",
    "weights": [0.000001, 0.0],  # y = 0.000001*x + 0
  },
  "leaf_models": [
    {"weights": [0.00001, 0.0]},
    {"weights": [0.00001, 100.0]},
    # ... 98 more leaf models
  ],
  "block_size": 10000  # Rows per block
}
```

#### Section 6: Column Groups Data (Variable)

Data organized by column groups (columns accessed together):

```
For each column group:
  Group ID (4 bytes, uint32)
  Column Count (4 bytes, uint32)
  For each column in group:
    Column Name (variable, null-terminated)
    Column Data Offset (8 bytes, uint64)
    Column Data Size (8 bytes, uint64)
    Compression Type (1 byte)
    Column Data:
      - Null Bitmap (if nullable)
        * 1 bit per row (1=null, 0=non-null)
        * Padded to byte boundary
      - Dictionary (if dictionary-encoded)
        * Dictionary size (4 bytes)
        * Dictionary entries (variable)
        * Index array (4 bytes per row)
      - Compressed Data (variable)
        * Raw bytes (compressed)
```

**Column Data Encoding**:

**Fixed-width types** (int32, float64, etc.):
```
[null_bitmap] [compressed_array]
```

**Variable-width types** (string, binary):
```
[null_bitmap] [offsets_array] [compressed_data]

Offsets: uint32 array, length = row_count + 1
  offsets[i] = start position of row i in data
  offsets[i+1] - offsets[i] = length of row i
```

**Dictionary-encoded strings**:
```
[null_bitmap] [dictionary] [indices]

Dictionary: [size:uint32] [entry1_len:uint32] [entry1_data] [entry2_len] [entry2_data] ...
Indices: uint32 array, length = row_count
```

#### Section 7: Footer & Offset Index (Variable)

```
Footer Structure:
  Magic Number (4 bytes): "NCFE" (0x4E 0x43 0x46 0x45)
  Footer Version (4 bytes, uint32)
  Metadata Size (4 bytes, uint32)
  Checksum Type (1 byte): 0=None, 1=CRC32, 2=XXHash
  File Checksum (32 bytes, SHA-256)
  Offset Index:
    Entry Count (4 bytes, uint32)
    For each entry:
      Section Name (16 bytes, null-padded)
      Section Offset (8 bytes, uint64)
      Section Size (8 bytes, uint64)
```

**Purpose**: Fast random access to sections, data integrity validation

---

## 4. Data Types

### 4.1 Supported Types

| Type | Size | Description | Example |
|------|------|-------------|---------|
| `int8` | 1 byte | Signed 8-bit integer | -128 to 127 |
| `int16` | 2 bytes | Signed 16-bit integer | -32,768 to 32,767 |
| `int32` | 4 bytes | Signed 32-bit integer | -2B to 2B |
| `int64` | 8 bytes | Signed 64-bit integer | -9E18 to 9E18 |
| `uint8` | 1 byte | Unsigned 8-bit integer | 0 to 255 |
| `uint16` | 2 bytes | Unsigned 16-bit integer | 0 to 65,535 |
| `uint32` | 4 bytes | Unsigned 32-bit integer | 0 to 4B |
| `uint64` | 8 bytes | Unsigned 64-bit integer | 0 to 18E18 |
| `float32` | 4 bytes | 32-bit floating point | IEEE 754 |
| `float64` | 8 bytes | 64-bit floating point | IEEE 754 |
| `boolean` | 1 bit | True/False | Packed bits |
| `string` | Variable | UTF-8 string | "Hello" |
| `binary` | Variable | Arbitrary bytes | b"\\x00\\xFF" |
| `date` | 4 bytes | Days since epoch | 2025-01-01 |
| `timestamp` | 8 bytes | Microseconds since epoch | 2025-01-01 12:00:00 |
| `decimal` | 16 bytes | Fixed-precision decimal | 123.45 |

### 4.2 Type Encoding

**Fixed-width types**: Stored as-is (little-endian)
**Variable-width types**: Offset array + data blob
**Booleans**: Bit-packed (8 values per byte)

---

## 5. Compression

### 5.1 Compression Levels

NCF supports 4 compression strategies:

1. **No Compression** (level 0)
   - Raw data storage
   - Fastest read/write
   - Use for: Already compressed data

2. **Standard Compression** (level 1)
   - ZSTD or LZ4
   - 5-10x compression
   - Use for: General purpose

3. **Dictionary Encoding** (level 2)
   - For low-cardinality strings
   - Separate dictionary + indices
   - Use for: Categorical columns

4. **Neural Compression** (level 3)
   - Learned autoencoder models
   - 12-15x compression
   - Use for: High-value large columns

### 5.2 Neural Compression

**Architecture**: Variational Autoencoder (VAE)

**Training Process**:
1. Sample 10-100K rows from column
2. Train VAE to compress → decompress
3. Validate reconstruction accuracy
4. Serialize model weights

**Model Size**: Typically 100KB-1MB (tiny vs data size)

**Compression Ratio**: 12-15x (vs 10x for ZSTD)

**Example**:
```python
# Train compression model
encoder = ColumnEncoder(column_type="string")
encoder.fit(sample_data)  # Train on 10K samples
compressed = encoder.encode(full_data)  # Compress all data

# Model stored in NCF file, used for decompression
decoder = ColumnDecoder.from_ncf(ncf_file, column_name)
original = decoder.decode(compressed)
```

---

## 6. Learned Indexes

### 6.1 Index Types

**RMI (Recursive Model Index)**:
- Hierarchy of linear models
- Root model → leaf models
- Best for: Sequential IDs, timestamps

**PGM (Piecewise Geometric Model)**:
- Piecewise linear approximation
- Adaptive segments
- Best for: Non-uniform distributions

**RadixSpline**:
- Radix tree + spline interpolation
- Fast lookups
- Best for: String keys

### 6.2 Index Structure

```python
# Learned index for column "id"
{
  "type": "rmi",
  "error_bound": 100,  # Max prediction error in rows
  "root_model": LinearModel(weights=[0.0001, 0]),
  "leaf_models": [LinearModel(...), ...],
  "block_size": 10000,
  "fallback_index": B_tree(...)  # If prediction fails
}
```

**Lookup Process**:
1. Query: `SELECT * FROM table WHERE id = 50000`
2. RMI prediction: `block = root_model(50000) = 5`
3. Read blocks 4-6 (±error_bound)
4. Binary search within blocks
5. Return result

**Size**: 0.1% of data (vs 10-20% for B-tree)

---

## 7. Column Groups

### 7.1 Purpose

Group columns that are frequently accessed together to:
- Reduce disk seeks
- Improve compression (similar data together)
- Enable vectorized processing

### 7.2 Grouping Strategy

**Automatic**:
- Analyze query logs
- Find columns accessed together
- Group by correlation

**Manual**:
- User-specified groups
- Example: `[user_id, email, name]` often queried together

### 7.3 Example

```python
# Table: users(id, email, name, created_at, last_login, preferences)

# Query pattern analysis:
# - 80% of queries: SELECT email, name WHERE ...
# - 15% of queries: SELECT created_at, last_login WHERE ...
# - 5% of queries: SELECT preferences WHERE ...

# Optimal grouping:
column_groups = {
  0: ["id"],                      # Primary key (always separate)
  1: ["email", "name"],           # Frequently accessed together
  2: ["created_at", "last_login"], # Time-series columns
  3: ["preferences"]              # Rarely accessed (separate)
}
```

---

## 8. Semantic Metadata

### 8.1 Purpose

Enable AI agents to understand data meaning and context:
- Auto-detect PII (emails, SSNs, names)
- Apply compliance rules automatically
- Optimize query strategies
- Generate smart suggestions

### 8.2 Semantic Types

```python
class SemanticType(Enum):
    UNKNOWN = "unknown"

    # PII Types
    PII_EMAIL = "pii_email"
    PII_PHONE = "pii_phone"
    PII_SSN = "pii_ssn"
    PII_NAME = "pii_name"
    PII_ADDRESS = "pii_address"

    # Geographic
    GEOGRAPHIC_LAT = "geo_lat"
    GEOGRAPHIC_LON = "geo_lon"

    # Temporal
    TEMPORAL_DATE = "temporal_date"
    TEMPORAL_TIMESTAMP = "temporal_timestamp"

    # Identifiers
    IDENTIFIER_UUID = "id_uuid"
    IDENTIFIER_KEY = "id_key"

    # General
    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    TEXT_DESCRIPTION = "text_description"
```

### 8.3 Usage by AI Agents

```python
# AI agent reads schema
schema = ncf_reader.read_schema()
email_col = schema.get_column("email")

if email_col.contains_pii:
    # Automatically mask PII in query results
    result = apply_pii_masking(result, email_col)

if email_col.semantic_type == SemanticType.PII_EMAIL:
    # Use email-specific optimizations
    use_email_learned_index()
    apply_email_regex_filters()
```

---

## 9. Example

### 9.1 Sample NCF File

**Table**: `users` with 1M rows

**Schema**:
```python
{
  "table_name": "users",
  "columns": [
    {"name": "id", "type": "int64", "semantic": "id_key"},
    {"name": "email", "type": "string", "semantic": "pii_email"},
    {"name": "name", "type": "string", "semantic": "pii_name"},
    {"name": "age", "type": "int32", "semantic": "numerical"},
    {"name": "created_at", "type": "timestamp", "semantic": "temporal_timestamp"}
  ]
}
```

**File Layout**:
```
users.ncf (32 MB total, 12.5x compression from 400 MB raw):

[0x00000000] Magic: "NCF\x01"
[0x00000004] Version: 1
[0x00000008] Header (60 bytes)
[0x00000044] Schema (2 KB, msgpack)
[0x00000844] Statistics (5 KB)
[0x00001A44] Learned Indexes (150 KB)
[0x00027244] Column Group 0: id (8 MB compressed)
[0x007D7244] Column Group 1: email, name (15 MB compressed)
[0x01527244] Column Group 2: age, created_at (8 MB compressed)
[0x01D27244] Footer (1 KB)
[0x01D27644] EOF
```

**Comparison**:
- **Raw size**: 400 MB
- **Parquet**: 40 MB (10x compression)
- **NCF**: 32 MB (12.5x compression, 20% better)

### 9.2 Read Example

```python
from neurolake.ncf import NCFReader

# Open NCF file
reader = NCFReader("users.ncf")

# Read schema only (fast)
schema = reader.read_schema()
print(schema.column_names())  # ['id', 'email', 'name', 'age', 'created_at']

# Read specific columns (projection pushdown)
df = reader.read(columns=["email", "name"])

# Read with filter (predicate pushdown)
df = reader.read(
    columns=["email", "name"],
    filter="age > 30"
)

# Close
reader.close()
```

---

## 10. Future Enhancements (v2.0)

1. **Multi-modal Support**: Store images, audio embeddings natively
2. **Adaptive Compression**: Change compression per block
3. **Incremental Updates**: Append-only modifications
4. **Distributed Indexes**: Learned indexes for partitioned data
5. **GPU Decompression**: Leverage GPU for neural decompression

---

## 11. References

- **Parquet Format**: https://parquet.apache.org/docs/
- **Learned Indexes (Kraska et al.)**: https://arxiv.org/abs/1712.01208
- **Neural Compression**: https://arxiv.org/abs/2001.09136

---

**Status**: Draft v1.0
**Next**: Implement writer/reader based on this spec
**Feedback**: feedback@neurolake.ai

---

**Copyright © 2025 NeuroLake. All rights reserved.**
