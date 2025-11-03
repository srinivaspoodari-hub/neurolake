"""
Validate NCF with real-world datasets

This script allows you to test NCF format with your own CSV/Parquet/Excel files
to verify correctness and performance with real data.
"""

import numpy as np
import pandas as pd
import tempfile
import os
import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neurolake.ncf.format.writer import NCFWriter
from neurolake.ncf.format.reader import NCFReader
from neurolake.ncf.format.schema import NCFSchema, ColumnSchema, NCFDataType


def infer_ncf_dtype(pandas_dtype):
    """Infer NCF data type from pandas dtype"""
    dtype_str = str(pandas_dtype)

    if dtype_str.startswith('int'):
        if 'int64' in dtype_str:
            return NCFDataType.INT64
        elif 'int32' in dtype_str:
            return NCFDataType.INT32
        elif 'int16' in dtype_str:
            return NCFDataType.INT16
        elif 'int8' in dtype_str:
            return NCFDataType.INT8
        else:
            return NCFDataType.INT64
    elif dtype_str.startswith('uint'):
        if 'uint64' in dtype_str:
            return NCFDataType.UINT64
        elif 'uint32' in dtype_str:
            return NCFDataType.UINT32
        elif 'uint16' in dtype_str:
            return NCFDataType.UINT16
        elif 'uint8' in dtype_str:
            return NCFDataType.UINT8
        else:
            return NCFDataType.UINT64
    elif dtype_str.startswith('float'):
        if 'float64' in dtype_str:
            return NCFDataType.FLOAT64
        elif 'float32' in dtype_str:
            return NCFDataType.FLOAT32
        else:
            return NCFDataType.FLOAT64
    elif dtype_str == 'object' or dtype_str.startswith('string'):
        return NCFDataType.STRING
    else:
        # Default to string for unknown types
        print(f"  [WARNING] Unknown dtype '{dtype_str}', treating as STRING")
        return NCFDataType.STRING


def create_schema_from_dataframe(df, table_name="real_data"):
    """Create NCF schema from pandas DataFrame"""
    columns = []
    for col_name in df.columns:
        ncf_dtype = infer_ncf_dtype(df[col_name].dtype)
        columns.append(ColumnSchema(name=col_name, data_type=ncf_dtype))

    return NCFSchema(table_name=table_name, columns=columns)


def validate_real_data(file_path, sample_size=None, verbose=True):
    """
    Validate NCF with a real dataset

    Args:
        file_path: Path to CSV/Parquet/Excel file
        sample_size: Optional - only use first N rows (for large files)
        verbose: Print detailed output

    Returns:
        dict with results
    """
    print("\n" + "=" * 70)
    print(f"VALIDATING NCF WITH REAL DATA: {Path(file_path).name}")
    print("=" * 70)

    # Load data
    print(f"\n[1/6] Loading data from {file_path}...")
    ext = Path(file_path).suffix.lower()

    try:
        if ext == '.csv':
            original_data = pd.read_csv(file_path, nrows=sample_size)
        elif ext == '.parquet':
            original_data = pd.read_parquet(file_path)
            if sample_size:
                original_data = original_data.head(sample_size)
        elif ext in ['.xlsx', '.xls']:
            original_data = pd.read_excel(file_path, nrows=sample_size)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        print(f"  [OK] Loaded {len(original_data):,} rows, {len(original_data.columns)} columns")
        print(f"  Columns: {list(original_data.columns)}")
        print(f"  Dtypes:\n{original_data.dtypes}")

        # Calculate original size
        original_size = original_data.memory_usage(deep=True).sum()
        print(f"  Memory usage: {original_size:,} bytes ({original_size/1024/1024:.2f} MB)")

    except Exception as e:
        print(f"  [ERROR] Failed to load data: {e}")
        return {"success": False, "error": str(e)}

    # Create schema
    print(f"\n[2/6] Creating NCF schema...")
    try:
        schema = create_schema_from_dataframe(original_data, table_name="real_data_test")
        print(f"  [OK] Schema created with {len(schema.columns)} columns")
    except Exception as e:
        print(f"  [ERROR] Failed to create schema: {e}")
        return {"success": False, "error": str(e)}

    # Write to NCF
    print(f"\n[3/6] Writing to NCF format...")
    with tempfile.NamedTemporaryFile(suffix=".ncf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        start_time = time.time()
        with NCFWriter(tmp_path, schema, compression="zstd") as writer:
            writer.write(original_data)
        write_time = time.time() - start_time

        ncf_size = os.path.getsize(tmp_path)
        print(f"  [OK] Wrote in {write_time:.3f}s")
        print(f"  NCF file size: {ncf_size:,} bytes ({ncf_size/1024/1024:.2f} MB)")
        print(f"  Compression ratio: {original_size/ncf_size:.2f}x")
        print(f"  Write speed: {len(original_data)/write_time:,.0f} rows/sec")

    except Exception as e:
        print(f"  [ERROR] Failed to write NCF: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return {"success": False, "error": str(e)}

    # Read from NCF
    print(f"\n[4/6] Reading from NCF format...")
    try:
        start_time = time.time()
        with NCFReader(tmp_path) as reader:
            # Validate checksum
            checksum_valid = reader.validate_checksum()
            print(f"  Checksum valid: {checksum_valid}")

            if not checksum_valid:
                print(f"  [WARNING] Checksum validation failed!")

            # Read data
            read_data = reader.read()

        read_time = time.time() - start_time
        print(f"  [OK] Read {len(read_data):,} rows in {read_time:.3f}s")
        print(f"  Read speed: {len(read_data)/read_time:,.0f} rows/sec")

    except Exception as e:
        print(f"  [ERROR] Failed to read NCF: {e}")
        import traceback
        traceback.print_exc()
        os.remove(tmp_path)
        return {"success": False, "error": str(e)}

    # Verify data integrity
    print(f"\n[5/6] Verifying data integrity...")
    try:
        # Check row count
        assert len(read_data) == len(original_data), \
            f"Row count mismatch: {len(read_data)} != {len(original_data)}"
        print(f"  [OK] Row count matches: {len(read_data):,}")

        # Check column names
        assert list(read_data.columns) == list(original_data.columns), \
            f"Column mismatch"
        print(f"  [OK] Column names match")

        # Check each column
        mismatches = []
        for col in original_data.columns:
            orig_col = original_data[col]
            read_col = read_data[col]

            # For numeric columns, use allclose
            if pd.api.types.is_numeric_dtype(orig_col):
                if not np.allclose(orig_col.values, read_col.values, equal_nan=True):
                    mismatches.append(f"{col} (numeric values differ)")
            else:
                # For string columns, compare directly
                if not list(orig_col) == list(read_col):
                    mismatches.append(f"{col} (string values differ)")

        if mismatches:
            print(f"  [WARNING] Column mismatches found:")
            for mismatch in mismatches:
                print(f"    - {mismatch}")
        else:
            print(f"  [OK] All column values match perfectly!")

    except Exception as e:
        print(f"  [ERROR] Data verification failed: {e}")
        import traceback
        traceback.print_exc()
        os.remove(tmp_path)
        return {"success": False, "error": str(e)}

    # Summary
    print(f"\n[6/6] Summary")
    print(f"  {'='*60}")
    print(f"  Original size: {original_size/1024/1024:.2f} MB")
    print(f"  NCF size: {ncf_size/1024/1024:.2f} MB")
    print(f"  Compression: {original_size/ncf_size:.2f}x")
    print(f"  Write speed: {len(original_data)/write_time:,.0f} rows/sec")
    print(f"  Read speed: {len(read_data)/read_time:,.0f} rows/sec")
    print(f"  Checksum valid: {checksum_valid}")
    print(f"  Data integrity: {'PASS' if not mismatches else 'FAIL'}")
    print(f"  {'='*60}")

    # Cleanup
    os.remove(tmp_path)

    return {
        "success": True,
        "rows": len(original_data),
        "columns": len(original_data.columns),
        "original_size_mb": original_size / 1024 / 1024,
        "ncf_size_mb": ncf_size / 1024 / 1024,
        "compression_ratio": original_size / ncf_size,
        "write_speed_rows_per_sec": len(original_data) / write_time,
        "read_speed_rows_per_sec": len(read_data) / read_time,
        "checksum_valid": checksum_valid,
        "data_integrity": not bool(mismatches),
        "mismatches": mismatches,
    }


def example_usage():
    """Show example usage"""
    print("\n" + "=" * 70)
    print("NCF REAL DATA VALIDATION - USAGE EXAMPLES")
    print("=" * 70)
    print("\nUsage:")
    print("  python validate_with_real_data.py <file_path> [sample_size]")
    print("\nExamples:")
    print("  # Test with full CSV file")
    print("  python validate_with_real_data.py data/sales.csv")
    print("\n  # Test with first 10,000 rows only")
    print("  python validate_with_real_data.py data/large_dataset.csv 10000")
    print("\n  # Test with Parquet file")
    print("  python validate_with_real_data.py data/transactions.parquet")
    print("\n  # Test with Excel file")
    print("  python validate_with_real_data.py data/report.xlsx")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        example_usage()
        sys.exit(1)

    file_path = sys.argv[1]
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    result = validate_real_data(file_path, sample_size=sample_size)

    if result["success"]:
        print("\n[SUCCESS] Real data validation completed!")
        sys.exit(0)
    else:
        print(f"\n[FAILED] Validation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
